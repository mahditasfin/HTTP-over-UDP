import os, math ,sys, datetime, socket, logging, threading, select, json

from multiprocessing import pool



class UDPSingleClientHandler(object):
    def __init__(self, buffer_size, payload_length):
        self.start_connection = True
        self.adress = ''
        self.payload = ''
        self.buffer = buffer_size
        self.payload = payload_length
        self.connections = []
        self.readable_thread = ''
        self.client_index = 0
        self.syn,self.fin,self.rst,self.ack,self.dat = False, False, False, False, False
        self.syn_ack, self.syn_ack_dat, self.syn_ack_dat_fin= False, False, False
        self.sender_queue = []
        self.retransmission_queue = []
    
    #first connection
    #analyze if the received packet has
        # syn
        # syn-ack
        # syn-ack-dat
        # syn-ack-dat-fin

    def extractHeader(self,payload):
        content = payload.decode('utf-8').split('\n')
        self.header = content[0]
        print(self.header)

    def commandCentre(self):
        print('INSIDE COMMAND CENTER\n\n')
        #here everything will go down
        if self.syn:
            #syn
            packet = 'ACK'+'\n'+'Sequence: '+str(0)+'\n'+'Length: '+str(0)+'\n'+'Acknowledgement: '+str(1)+'\n'+'Windows: '+str(0)
            self.sender_queue.append('Server')
            date_time = datetime.datetime.now().strftime("%a %d %b %H:%M:%S PDT %Y")
            print(date_time+',Send;',+';','Sequence:',str(0),';Length:',str(0),self.adress)
            self.retransmission_queue.append(packet)
            self.transmit(packet)
            print('COMMAND : SYN')
        elif self.syn and self.ack:
            self.syn_ack = True
            print('COMMAND : SYN|ACK')
        elif self.syn and self.ack and self.dat:
            #straight data sending
            self.syn_ack_dat = True
            print('COMMAND : SYN|ACK|DAT')
        elif self.syn and self.ack and self.dat and self.fin:
            self.syn_ack_dat_fin = True
            # straight data sending
            print('COMMAND : SYN|ACK|DAT')
     
        

    def initConnection(self,payload):
        #syn here
        print('client level: Extracting headers from payload')
        commands = self.header.split('|')
        if len(commands) > 0:
            #the first command received for each client
            for i in commands:
                if i == 'SYN':
                    print('Has SYN')
                    self.syn = True
                
                if i == 'ACK':
                    print('Has ACK')
                    self.ack = True
                
                if i == 'DAT':
                    print('Has DAT')
                    self.dat = True
                
                if i == 'FIN':
                    print('Has FIN')
                    self.fin = True

        

    #every next payload after init connection
    #work on it after 2nd packet starts coming
    def receivedPayload(self, payload):
        self.extractHeader(payload)
        print('2nd packet', payload)


    def transmit(self, payload):
        if self.senderQueue.pop(0):
            self.sock.sendto((payload).encode('utf-8'), self.adress)
        

    #run will start initial connection
    def run(self,client_adress, payload):
        self.adress = client_adress
        self.extractHeader(payload)
        self.initConnection(payload)
    
        print('reached here')




#work done 

class UDPMultiClientHandler(object):
    def __init__(self, buffer_size, payload_length):
        self.start_connection = True
        self.payload = ''
        self.buffer = buffer_size
        self.payload_len = payload_length
        self.connections = []
        self.client_generic_name = 'client-'
        self.client_counter = 0
        self.readable_thread = ''
        print('Made Object')

    #start each client
    def startSingleClientHandler(self, client_adress,payload):
        self.client_counter = self.client_counter+1
        print('only for new clients\n',self.client_counter,'\n\n')
        client_reg = {}
        client_name= self.client_generic_name + str(self.client_counter)
        client_reg[client_name],client_reg['client-address']=UDPSingleClientHandler(self.buffer, self.payload),client_adress[1]
        client_reg[client_name].run(client_adress, payload)
        self.connections.append(client_reg)

    #searches through the list of connections
    def search(self, client_address):
        for items in self.connections:
                if items['client-address'] == client_address[1]:
                    return self.connections.index(items)
        return -1
                
            
    #checks if client exists everytime readable is triggered
    def checkClientExists(self, payload, client_address):
        #very first connection
        if not self.connections:
            print('starting 1st client\n\n')
            self.startSingleClientHandler(client_address,payload)
        elif self.connections:
            #very every other connections from the 2nd o
            client_exist = self.search(client_address)
            counter = client_exist+1
            if client_exist>=0:
                print('Client is registered')
                self.connections[client_exist][self.client_generic_name + str(counter)].receivedPayload(payload)
            elif client_exist == -1:
                self.startSingleClientHandler(client_address,payload)

    def run(self):
        self.start_connection = False
        
        



def checkClient(client_data, client_address):
    pass



def startConnectionThread():
    host = str(sys.argv[1])
    port = int(sys.argv[2])
    buffer_size = sys.argv[3]
    payload_length = sys.argv[4]

    all_connections = []

    logger = logging.getLogger()

    #setup socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(0)
    sock.bind((host,port))
    potential_reader = [sock]
    potential_writer = [sock]
    primeServer = UDPMultiClientHandler(buffer_size,payload_length)


    if primeServer.start_connection:
        primeServer.run()
    
    init_Connection = False
        

    counter = 1
    try:
        while True:
            readable, writable, exceptional = select.select(potential_reader, potential_writer, potential_reader,2)
            if sock in writable:
                # UDPMultiClientHandler.writabaletriggered()
                potential_writer.remove(sock)


            if sock in readable:
                counter= counter+1
                client_data, client_address = sock.recvfrom(int(buffer_size))
                print(client_address,'triggered \n\n')
                if client_data:
                    primeServer.checkClientExists(client_data, client_address)
                    potential_writer.append(sock)

            if not (readable or writable or exceptional):
                potential_writer.append(sock)
                # jointClientServer.retransmit()

    except IOError:
        print('keyboard interrupt, exiting')
    sock.close()


if __name__ == '__main__':
    startConnection = threading.Thread(target=startConnectionThread())
    startConnection.start()

import os, math ,sys, datetime, socket, logging, threading, select, json

from multiprocessing import pool
from types import prepare_class


global length_last_try

class UDPSingleClientHandler(object):
    def __init__(self, buffer_size, length, sock):
        self.start_connection = True
        self.first_packet_received = False
        self.address =''
        self.header = ''
        self.body = ''
        self.buffer = buffer_size
        print(length,'packet length')
        self.packet_length = 0
        self.connections = []
        self.readable_thread = ''
        self.client_index = 0
        self.syn,self.fin,self.rst,self.ack,self.dat = False, False, False, False, False
        self.syn_ack,self.ack_dat, self.syn_ack_dat, self.syn_ack_dat_fin= False, False, False, False
        self.sender_queue = []
        self.retransmission_queue = []
        self.sock = sock
        self.num_commands = 0
        self.expecting_flag = ''
        self.seq,self.len,self.ack_num_received,self.window_size_received = 0,0,0,0
        self.MTU = 576
        self.request = ''
        self.requested_file = ''
        self.file_buffer = ''
        self.file_size = 0
        self.data_packets = []
        self.data_packets_left = 0
        self.connection_alive = False
        self.connection_close = False
        self.sender_seq = 1
        self.sender_ack = 1
        self.successful_req = 'HTTP/1.0 200 OK'
        self.next_file = False
        self.ready_packets = []
        self.expected_ack = []
        self.total_bytes_sent = 0
        self.contains_data = False
        self.mean_time_Q = []
        self.sent_mean_time_Q = []
        self.handshake = False


    def extractHeader(self,payload):
        content = payload.decode('utf-8').split('\r\n')
        self.header = content[0].split('\n')
        if len(content)>1:
            self.contains_data = True
            self.body = content[1]
        self.seq = int(self.header[1].split(':')[1])
        self.len = int(self.header[2].split(':')[1])
        self.ack_num_received = int(self.header[3].split(':')[1])
        if self.seq == 0:
            self.sender_ack = self.seq + self.len+1
        self.sender_ack = self.seq + self.len+1
        self.window_size_received = int(self.header[4].split(':')[1])
        print('Sequence:'+str(self.seq) +'Acknowledgement:' +str(self.ack_num_received) +'Window Size Received'+ str(self.window_size_received)+'ack for next packet' +str(self.sender_ack)+'\n\n\n' + 'length'+str(self.len))

    def checkMeantTimeAck(self):
        for ack in self.expected_ack[:]:
            for ack2 in self.mean_time_Q:
                if ack == ack2:
                    self.expected_ack.remove(ack2)
        self.mean_time_Q.clear()

    #this method checks self.exoected_flag for each n+1 data packets received 
    def checkAck(self):
        # initial expected ack
        for expected_ack in self.expected_ack:

            if self.ack_num_received ==  expected_ack and self.ack_num_received == self.expected_ack[0]:
                self.expected_ack.pop(0)
                self.mean_time_Q.append(self.ack_num_received)
                self.checkMeantTimeAck()
                self.sendData()
            #ack in there but not initial
            elif expected_ack == self.ack_num_received and expected_ack!=self.expected_ack[0]:
                self.mean_time_Q.append(self.ack_num_received)
                         

    def commandCentre(self):
        print('INSIDE COMMAND CENTER actual\n\n')
        #here everything will go down
        print(self.syn,self.ack,self.dat,self.fin, self.num_commands)
        if self.syn and self.num_commands == 1 and self.ack_num_received == -1:
            #syn
            packet = 'ACK'+'\n'+'Sequence: '+str(0)+'\n'+'Length: '+str(0)+'\n'+'Acknowledgement: '+str(1)+'\n'+'Windows: '+str(0)
            self.sender_queue.append('Server')
            self.retransmission_queue.append(packet)
            self.transmit(packet)
            #always checked on the 2nd packet
            self.expecting_flag = 'ACK'
            print('COMMAND : SYN')
        #add fin
        elif self.ack and self.num_commands == 1 and self.ack_num_received !=1:
            print('received Ack')
            self.checkAck()
        elif self.dat and self.ack and not self.syn and self.ack_num_received == 1:
            self.ack_dat = True
            self.handshake = True
            print('COMMAND: DAT|ACK')
            self.initSending()
    
            #another file incoming
        elif self.dat and self.ack and not self.syn and self.ack_num_received !=1:
            self.handshake = True
            self.ack_dat = True
            if self.retransmission_queue:
                self.retransmission_queue.pop(0)
            print('emptying data packets')
            print('COMMAND: DAT|ACK,received Ack|DAT with ACk!= 1')
            self.initSending()     
        elif self.syn and self.ack and self.num_commands == 2:
            self.syn_ack = True
            print('COMMAND : SYN|ACK')
            packet = 'SYN|ACK'+'\n'+'Sequence: '+str(0)+'\n'+'Length: '+str(0)+'\n'+'Acknowledgement: '+str(1)+'\n'+'Windows: '+str(0)
            self.sender_queue.append('Server')
            self.retransmission_queue.append(packet)
            self.transmit(packet)
            self.expecting_flag = 'ACK|DAT'
        elif self.syn and self.ack and self.dat and self.num_commands == 3 and self.ack_num_received == -1:
            print(self.connection_alive, self.connection_close)
            #straight data sending
            self.syn_ack_dat = True
            print('COMMAND : SYN|ACK|DAT')
            self.initSending()
        elif self.syn and self.ack and self.dat and self.fin and self.num_commands == 4 and self.ack_num_received == -1:
            self.syn_ack_dat_fin = True
            print('COMMAND : SYN|ACK|DAT|FIN', self.syn_ack_dat_fin)
            self.initSending()
            #straight data sending



    def initSending(self):
        self.request = self.body.split(' ')[0]
        self.requested_file = self.request.split('/')[1]
        self.checkPersistentHTTP()
        self.createDataPackets()
        self.addHeaderAndExpectedAck()
        self.sendData()


    # receiver = 8120
    # data packets can bent = receiver / mss
    # 10 packets-8120
    def sendData(self):
        if self.data_packets_left <= math.floor(self.window_size_received/int(sys.argv[4])):
            for i in self.ready_packets[:]:     
                self.retransmission_queue.append(i)
                self.sender_queue.append('sending files')
                self.transmit(i)
                self.ready_packets.remove(i)
                # self.sent_mean_time_Q.append(self.expected_ack[i])
                self.data_packets_left -=1
        elif self.data_packets_left > math.floor(self.window_size_received/int(sys.argv[4])):
            packet_can_be_sent = math.floor(self.window_size_received/int(sys.argv[4]))
            for i in range(0,packet_can_be_sent):
                for i in self.ready_packets:
                    self.retransmission_queue.append(i)
                    self.sender_queue.append('sending files')
                    self.transmit(i)
                    # self.sent_mean_time_Q.append(i)
                    self.data_packets_left-=1
                    self.ready_packets.remove(i)
        for i in self.data_packets:
            self.data_packets.pop()

        
    
    def checkPersistentHTTP(self):
        persistent =''
        if self.contains_data:
            body = self.body.split('\n')
            if len(body)>1:
                persistent = body[1]
            
            print(persistent)
            if persistent == 'Connection:keep-alive':
                self.connection_alive = True
                print('Keep-alive')
            elif persistent == 'Connection:Keep-alive':
                self.connection_alive = True
                print('keep-alive')
            elif persistent == 'Connection:close':
                self.connection_alive = False
                print('close')
            else:
                self.connection_alive = False
                print('close')

        
    def singlePacket(self,packet):
        print(self.syn_ack_dat,self.syn_ack_dat_fin,self.connection_close,self.connection_alive)
        if self.syn_ack_dat or self.syn_ack_dat_fin or self.ack_dat and not self.connection_alive:
            comm = 'SYN|ACK|DAT|FIN'
            if self.handshake == True:
                comm = 'ACK|DAT|FIN'

            ready_packet = comm+'\n'+'Sequence: '+str(self.sender_seq)+'\n'+'Length: '+str(len(packet))+'\n'+'Acknowledgement: '+str(self.sender_ack+1)+'\n'+'Windows: '+str(0) + '\n'+'Content-length: '+str(self.file_size)+'\n'+self.successful_req +'\r\n' + packet
            self.sender_queue.append('dummy')
            print('single pack sending ack',self.sender_ack, self.sender_seq, ready_packet)
            self.retransmission_queue.append(ready_packet)
            self.transmit(ready_packet)
            self.expecting_flag = 'FIN|ACK'
            self.handshake = False
            self.data_packets_left -=1

            #wait for client to send more
        elif self.syn_ack_dat or self.syn_ack or self.ack_dat and self.connection_alive:
    
            if self.handshake == True:
                comm = 'DAT|ACK'
            comm = 'SYN|ACK|DAT'
            ready_packet = comm+'\n'+'Sequence: '+str(self.sender_seq)+'\n'+'Length: '+str(len(packet))+'\n'+'Acknowledgement: '+str(self.sender_ack+1)+'\n'+'Windows: '+str(0) +'\n'+'Content-length: '+str(self.file_size)+'\n'+ '\r\n'+self.successful_req+'\n'+'Connection: keep-alive' +'\r\n' + packet.decode('utf-8')
            self.sender_queue.append('dummy')
            self.retransmission_queue.append(ready_packet)
            self.transmit(ready_packet)
            self.expecting_flag = 'ACK'
            self.handshake = False
            self.data_packets_left -=1

    def addHeaderAndExpectedAck(self):
        print('inside add header and expected ack')
        if len(self.data_packets) == 1:
                print('contains only one packet')
                self.singlePacket(self.data_packets[0])
        elif len(self.data_packets)>1:
            for packet in self.data_packets:
                seq = self.total_bytes_sent+1
                length = len(packet)
                print(self.total_bytes_sent)
                if self.data_packets.index(packet)+1 == 1:
                    temp ='\r\n'
                    temp2 = 'SYN|ACK|DAT'
                    if self.connection_alive:
                        temp = '\nConnection: keep-alive\r\n'
                    if self.handshake:
                        temp2 = 'DAT|ACK'
                    ready_packet = temp2+'\n'+'Sequence: '+str(seq)+'\n'+'Length: '+str(length)+'\n'+'Acknowledgement: '+str(self.sender_ack)+'\n'+'Windows: '+str(0) +'\n'+'Content-length: '+str(self.file_size)+'\r\n'+self.successful_req +temp + packet
                    self.ready_packets.append(ready_packet) 
                    self.handshake = False
                elif self.data_packets.index(packet)+1 == len(self.data_packets) and not self.connection_alive:
                    ready_packet = 'ACK|DAT|FIN'+'\n'+'Sequence: '+str(seq)+'\n'+'Length: '+str(length)+'\n'+'Acknowledgement: '+str(self.sender_ack)+'\n'+'Windows: '+str(0) +'\r\n' + packet                   

                    self.ready_packets.append(ready_packet)
                elif self.data_packets.index(packet)+1 == len(self.data_packets):
                    ready_packet = 'ACK|DAT'+'\n'+'Sequence: '+str(seq)+'\n'+'Length: '+str(length)+'\n'+'Acknowledgement: '+str(self.sender_ack)+'\n'+'Windows: '+str(0) +'\r\n' + packet                

                    self.ready_packets.append(ready_packet)
                else:
                    #regular packets
                    ready_packet = 'ACK|DAT'+'\n'+'Sequence: '+str(seq)+'\n'+'Length: '+str(length)+'\n'+'Acknowledgement: '+str(self.sender_ack)+'\n'+'Windows: '+str(0) + '\r\n'+ packet
                    self.ready_packets.append(ready_packet)
            self.total_bytes_sent += len(packet)
            self.expected_ack.append(self.total_bytes_sent+1)
        self.data_packets_left = len(self.data_packets)
   




                        

            
            #send fin
            # if self.data_packets.index(packet) == len(self.data_packets):
            #     if self.connection_close:
            #         pass




        
    def createDataPackets(self):
        print('Requested file :', self.requested_file)

        self.file_size = os.path.getsize(self.requested_file)
        if self.file_size:
            with open(self.requested_file,'rb') as f:
                data = f.read(int(sys.argv[4]))
                self.data_packets.append(data.decode('utf-8'))
                while len(data) != 0:
                    data = f.read(int(sys.argv[4]))
                    self.data_packets.append(data.decode('utf-8'))
        self.data_packets.pop(-1)
        

    
    
    def resetRetransmission(self):
        pass

    
    
    def resetFlagsAfterSending(self):
        self.syn,self.fin,self.rst,self.ack,self.dat = False, False, False, False, False
        self.syn_ack, self.syn_ack_dat, self.syn_ack_dat_fin= False, False, False
       

    
    
    def sendResetFlag(self, commands):
        packet = 'RST'+'\n'+'Sequence: '+str(0)+'\n'+'Length: '+str(0)+'\n'+'Acknowledgement: '+str(-1)+'\n'+'Windows: '+str(0)
        if not 'SYN' in commands:
            self.sender_queue.append('Server')
            self.retransmission_queue.append(packet)
            self.transmit(packet)
        else:
            if ('SYN' and 'FIN' and not 'ACK' and not 'DAT') in commands:
                self.sender_queue.append('Server')
                self.retransmission_queue.append(packet)
                self.transmit(packet)  
            elif ('SYN' and ('DAT' or 'FIN') and not 'ACK') in commands:
                self.sender_queue.append('Server')
                self.retransmission_queue.append(packet)
                self.transmit(packet)  
        if (self.window_size_received < self.MTU):
            self.sender_queue.append('Server')
            self.retransmission_queue.append(packet)
            self.transmit(packet)
       



    def initConnection(self,payload):
        #syn here
        print('client level: Extracting headers from payload')
        commands = self.header[0].split('|')
        self.num_commands = len(commands)
        print(commands)
        if self.first_packet_received:
            #check if contains syn and check if window_size_received >= mss+20(for ipv4 headers) and MTU 576
            #send reset flag
            self.sendResetFlag(commands)
            self.first_packet_received = False
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
        self.initConnection(payload)
        self.commandCentre()


    
    
    
    def transmit(self, payload):
        print(self.address, 'transmitting')
        if self.sender_queue.pop(0):
            self.sock.sendto((payload).encode('utf-8'), (self.address))
            self.resetFlagsAfterSending()
       


    #run will start initial connection
    def run(self,client_adress, payload, length):
        self.first_packet_received = True
        self.packet_length = length

        self.address = client_adress
        self.extractHeader(payload)
        self.initConnection(payload)
        self.commandCentre()

        



#work done 

class UDPMultiClientHandler(object):
    def __init__(self, buffer_size, payload_length):
        self.start_connection = True
        self.buffer = buffer_size
        self.payload_len = payload_length
        print(self.payload_len)
        self.connections = []
        self.client_generic_name = 'client-'
        self.client_counter = 0
        self.readable_thread = ''
        print('Made Object')

    #start each client
    def startSingleClientHandler(self, client_adress,payload,sock):
        self.client_counter = self.client_counter+1
        print('only for new clients\n',self.client_counter,'\n\n')
        client_reg = {}
        client_name= self.client_generic_name + str(self.client_counter)
        print(self.payload_len)
        client_reg[client_name],client_reg['client-address']=UDPSingleClientHandler(self.buffer, self.payload_len,sock),client_adress[1]
        client_reg[client_name].run(client_adress, payload, self.payload_len)
        self.connections.append(client_reg)

    #searches through the list of connections
    def search(self, client_address):
        for items in self.connections:
                if items['client-address'] == client_address[1]:
                    return self.connections.index(items)
        return -1
                
            
    #checks if client exists everytime readable is triggered
    def checkClientExists(self, payload, client_address,sock):
        #very first connection
        if not self.connections:
            print('starting 1st client\n\n')
            self.startSingleClientHandler(client_address,payload,sock)
        elif self.connections:
            #very every other connections from the 2nd o
            client_exist = self.search(client_address)
            counter = client_exist+1
            if client_exist>=0:
                print('Client is registered')
                self.connections[client_exist][self.client_generic_name + str(counter)].receivedPayload(payload)
            elif client_exist == -1:
                self.startSingleClientHandler(client_address,payload,sock)

    def run(self):
        self.start_connection = False
        
        






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
        

    counter = 0
    try:
        while True:
            readable, writable, exceptional = select.select(potential_reader, potential_writer, potential_reader,2)
            if sock in writable:
                # UDPMultiClientHandler.writabaletriggered()
                potential_writer.remove(sock)


            if sock in readable:
                counter= counter+1
                client_data, client_address = sock.recvfrom(int(buffer_size))
                print(client_data.decode('utf-8').splitlines()[3],'triggered \n\n')
              
#                 sock.sendto(client_data,client_address)
                if client_data:
                    primeServer.checkClientExists(client_data, client_address,sock)
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

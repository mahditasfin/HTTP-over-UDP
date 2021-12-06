import time
from logging import fatal
from os import read
import socket, threading, selectors, sys, select
init_connection = True

#create packeting which can be used in the server code
#initiate client connection
sel = selectors.DefaultSelector()
read_File_List = []
write_File_List_= []
client_packets=[]
messages = [b"GET/sws.py/HTTP/1.0"]

class UDPClientHandler(object):
    def __init__(self, input_files, output_files, buffer, payload_len, sock, server):
        #start initializing variable:
        self.socket = sock
        self.server = server
        self.read_files = input_files
        self.write_files = output_files
        self.buffer = buffer
        self.payload_length = payload_len
        self.header = ''     
        #lists
        self.packet_buffer = []
        self.flags = dict()
        #start setting flags only after responses
        self.past_flag=''
        self.flags['SYN'], self.flags['DAT'], self.flags['ACK'], self.flags['FIN'], self.flags['RST']='','','','',''
        self.window_size = 5120


    def sendAfterAnalyzingPayload():
        pass
        #only will reach here after ack is received
        #SYN|ACK|DAT
        #SYN|ACK|DAT|FIN
        #SYN|ACK
        #if ACK:
         #ack == -1:
         #ack == 1:
            #send dat if it contains only ACK
         #ack > 1:
            #check ack of last packet sent
         #ack > windowsize:
            #rst
         #last_ack_received*3 = retransmit
            #retransmit


    def clientErrorControl():
        pass
        #only will come here once sending DAT
        #add to retransQ while sending packets
        #the next req will only be sent when the content-length is met
        #except for that only ack for data packets will be sent




    def analyzeReceivedPayload():
        pass
        #extract command off payload
        #if command contains: SYN and DAT because client sent SYN|ACK|DAT
            #server initiated
            #also sent the first packet
        #id command contains only ACK if client sends SYN:
            #if last packet sent is SYN
            #server sends ACK
            #send DAT with req
            #wait for ACK
            #then syn-ack
            #send ACK
            #start receiving DATA
        #id command doest not contain SYN:
            #id command contains DAT|ACK
                #packets in the middle
            #id commnd contain DAT|ACK|FIN
                #last packet

  # SYN|DAT|ACK
    # Sequence: 0
    # Length: 48
    # Acknowledgment: -1
    # Window: 4096
    # GET /sws.py HTTP/1.0
    # Connection: keep-alive
    
    def initConnection(self):
        if self.initConnection:
            if len(self.read_files) > 1:
                print('starting connection')
                packet1 = 'SYN'+'\n'+'Sequence: '+str(0)+'\n'+'Length: '+str(0)+'\n'+'Acknowledgement: '+str(-1)+'\n'+'Windows: '+str(self.window_size)
                packet2 = 'SYN|ACK'+'\n'+'Sequence: '+str(0)+'\n'+'Length: '+str(0)+'\n'+'Acknowledgement: '+str(-1)+'\n'+'Windows: '+str(self.window_size)
                packet3 = 'SYN|ACK|DAT|FIN'+'\n'+'Sequence: '+str(0)+'\n'+'Length: '+str(0)+'\n'+'Acknowledgement: '+str(-1)+'\n'+'Windows: '+str(self.window_size)
                packet4 = 'SYN|ACK|DAT'+'\n'+'Sequence: '+str(0)+'\n'+'Length: '+str(0)+'\n'+'Acknowledgement: '+str(-1)+'\n'+'Windows: '+str(self.window_size)
                packet5 = 'SYN|ACK'+'\n'+'Sequence: '+str(0)+'\n'+'Length: '+str(0)+'\n'+'Acknowledgement: '+str(-1)+'\n'+'Windows: '+str(self.window_size)
                self.socket.sendto(packet1.encode('utf-8'), self.server)
                time.sleep(1)
                self.socket.sendto(packet2.encode('utf-8'), self.server)
                # self.socket.sendto(packet3.encode('utf-8'), self.server)
                # self.socket.sendto(packet4.encode('utf-8'), self.server)
                # self.socket.sendto(packet5.encode('utf-8'), self.server)
            elif len(self.read_files) == 1:
                packet = 'SYN|DAT|ACK|FIN'+'\n'+'Sequence: '+str(0)+'\n'+'Length: '+str(len(self.read_files[0]))+'\n'+'Acknowledgement: '+str(0)+'\n'+'Windows: '+str(self.window_size)+'\n\n'+'GET/'+self.read_files[0]+' HTTP/1.0'+'\n'
                self.packet_buffer.append(packet)

            

    def sendPackets(self):
        pass
    def createDataPackets(self):
        packet=''
        seq = 0
        ack = 1
        if len(self.read_files)>1:
            for i in range(0,len(self.read_files)):
                #for packet no 1
                if i == len(self.read_files)-1:
                    packet = 'DAT|ACK'+'\n'+'Sequence: '+str(seq)+'\n'+'Length: '+str(len(self.read_files[i]))+'\n'+'Acknowledgement: '+str(ack)+'\n'+'Windows: '+str(self.window_size)+'\n\n'+'GET/'+self.read_files[i]+' HTTP/1.0'+'\n'
                    self.packet_buffer.append(packet)
                    
                else:
                    packet = 'DAT|ACK'+'\n'+'Sequence: '+str(seq)+'\n'+'Length: '+str(len(self.read_files[i]))+'\n'+'Acknowledgement: '+str(ack)+'\n'+'Windows: '+str(self.window_size)+'\n\n'+'GET/'+self.read_files[i]+' HTTP/1.0'+'\n'+'Connection:keep-alive'
                    self.packet_buffer.append(packet)
                #seq check laters
                seq = len(self.read_files[i])+1+seq
                # ack will be updated when receiving starts
                ack = 1
        elif len(self.read_files) == 1:
                packet = 'DAT|ACK|FIN'+'\n'+'Sequence: '+str(seq)+'\n'+'Length: '+str(len(self.read_files[0]))+'\n'+'Acknowledgement: '+str(ack)+'\n'+'Windows: '+str(self.window_size)+'\n\n'+'GET/'+self.read_files[0]+' HTTP/1.0'+'\n'
                self.packet_buffer.append(packet)

                
        for i in self.packet_buffer:
            print(i,'\n\n')
                                                                                                                                                                                                
    def run(self):
        #first start reading from file
        self.createDataPackets()
        self.initConnection()
            
        #self.packet_buffer contains the packets
        self.sendPackets()
        # #write_a_receiver_triggered_function
        # self.readabledTriggered(payload)
        # #analyse command
        # self.analyzeReceivedHeader()
        # #if correct ACK
        # self.sendPackets()



        pass



def startClientConnectionThread():
    host = 'localhost'
    port = int(sys.argv[2])
    client_Buffer = int(sys.argv[3])
    client_MSS = int(sys.argv[4])


    if len(sys.argv)>5:
        total_File_Couples = ((len(sys.argv)-5)/2)
        print(sys.argv,total_File_Couples, len(sys.argv))
        print(total_File_Couples/2)
        if total_File_Couples*2%2 == 0.0:
            print('here')
            counter = 0
            for i in range(0,int(total_File_Couples)):
                print(5+counter,5+1+counter)
                read_File_List.append(sys.argv[5+counter])
                write_File_List_.append(sys.argv[5+counter+1])
                print(counter)
                if counter == 0:
                    counter = counter+1
                if counter != 0:
                    if counter == 1:
                        counter = counter*2
                    else:
                        counter = counter+2
        else:
            print("Inconsistent read and write file combination")
            sys.exit()
    print(read_File_List,write_File_List_)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(0)
    potential_reader = [sock]
    potential_writer = [sock]
    server = (host,port)

    if init_connection:
        client_online = UDPClientHandler(read_File_List,write_File_List_,client_Buffer,client_MSS, sock, server)
        client_online.run()
        

    try:
        while True:
            readable, writable, exceptional = select.select(potential_reader, potential_writer, potential_reader,1)
            if sock in writable:
                potential_writer.remove(sock)


            #analyze payload command
            if sock in readable:
                counter= counter+1
                clientData, clientAddress = sock.recvfrom(client_Buffer)
                # analyzeReceivedPayload(clientData)
                print(clientData)
                potential_writer.append(sock)

            if not (readable or writable or exceptional):
                potential_writer.append(sock)

    except IOError:
        print('keyboard interrupt, exiting')
    sock.close()
# python3 sor-client.py 134.87.131.31 80 8120 512 dumm01.txt copy01.txt dummy02.txt copy02.txt dummy03.txt copy03.txt

if __name__ == '__main__':
    startClientConnection = threading.Thread(target = startClientConnectionThread())
    startClientConnection.start()

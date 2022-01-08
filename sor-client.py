import time
import datetime, re
from logging import fatal
from os import read, stat
import socket, threading, selectors, sys, select
init_connection = True



class UDPClientHandler(object):
    def __init__(self, input_files, output_files, buffer, payload_len, sock, server):
        #start initializing variable:
        self.socket = sock
        self.server = server
        self.good_response = 'HTTP/1.0 200 OK'
        self.read_files = input_files
        self.write_files = output_files
        self.buffer = buffer
        self.payload_length = payload_len
        self.header = ''
        self.start_reciveing_data = False   
        self.current_file_bytes = 0  
        #lists
        self.packet_buffer = []
        self.flags = dict()
        #start setting flags only after responses
        self.past_flag=''
        self.window_size = 5120
        self.syn,self.fin,self.rst,self.ack,self.dat = False, False, False, False, False
        self.ack_dat,self.ack_Dat_fin,self.syn_ack_dat, self.syn_ack_dat_fin= False,False, False, False
        self.ack_num_received, self.seq, self.window_size_received = 0,0,0
        self.sender_queue = []
        self.num_commands = 0
        self.retransmission_queue = []
        self.packet1 = 'SYN'+'\n'+'Sequence: '+str(0)+'\n'+'Length: '+str(0)+'\n'+'Acknowledgement: '+str(-1)+'\n'+'Windows: '+str(self.window_size)
        self.packet2 = 'SYN|ACK'+'\n'+'Sequence: '+str(0)+'\n'+'Length: '+str(0)+'\n'+'Acknowledgement: '+str(-1)+'\n'+'Windows: '+str(self.window_size)
        self.packet3 = 'SYN|ACK|DAT|FIN'+'\n'+'Sequence: '+str(0)+'\n'+'Length: '+str(0)+'\n'+'Acknowledgement: '+str(-1)+'\n'+'Windows: '+str(self.window_size)
        self.packet4 = 'SYN|ACK|DAT'+'\n'+'Sequence: '+str(0)+'\n'+'Length: '+str(0)+'\n'+'Acknowledgement: '+str(-1)+'\n'+'Windows: '+str(self.window_size) + ''
        self.reset_packet1 = 'SYN|FIN'+'\n'+'Sequence: '+str(0)+'\n'+'Length: '+str(0)+'\n'+'Acknowledgement: '+str(-1)+'\n'+'Windows: '+str(243)  
        self.persistent_connection = False
        self.sequence = 0
        self.ack_num = 0
        self.len = 0
        self.acknowledgement = 0
        self.expected_ack = 0
        self.updated_ack = 0
        self.total_files = len(input_files)
        self.body = ''
        self.status = ''
        self.pause_receiving_data = False
        self.bytes_received = 0
        self.content_length = 0
        self.files_sent = 0
        self.current_write_file = ''
        self.total_bytes_sent = 0
        self.error_encountered = False
        self.file_packets_received = []
        self.commands = ''
        self.body_at = 0
        self.keep_alive = ''
        self.total_bytes_received = 0


        
    def resetFlagsAfterSending(self):
        self.syn,self.fin,self.rst,self.ack,self.dat = False, False, False, False, False
        self.syn_ack, self.syn_ack_dat, self.syn_ack_dat_fin= False, False, False
        self.len, self.seq = 0,0
    
    def initConnection(self):
        if self.initConnection:
            if len(self.read_files) > 1:
                self.persistent_connection = True
                self.expected_ack = 1
                print('Send SYN|ACK')
                self.sender_queue.append("Sending")
                self.retransmission_queue.append(self.packet2)
                self.transmit(self.packet2)
            elif len(self.read_files) == 1:
                self.persistent_connection = False
                body = 'GET/'+self.read_files[0]+' HTTP/1.0'
                packet = 'SYN|DAT|ACK|FIN'+'\n'+'Sequence: '+str(0)+'\n'+'Length: '+str(len(body))+'\n'+'Acknowledgement: '+str(-1)+'\n'+'Windows: '+str(self.window_size)+'\r\n'+body
                print('len of body', len(body), 'expected ack: ', self.expected_ack)
                self.expected_ack = len(body)+1
                # print(self.expected_ack)
                self.sender_queue.append('Request for one file')
                self.retransmission_queue.append(packet)
                self.transmit(packet)
                self.current_write_file = self.write_files[0]
                self.start_reciveing_data = True

    
    def analyzeHeader(self):
        #syn her
        commands = self.commands.split('|')
        self.num_commands = len(commands)
        print(commands)
        if len(commands) > 0:
            #the first command received for each client
            for i in commands:
                if i == 'SYN':
                    self.syn = True
                
                if i == 'ACK':

                    self.ack = True
                
                if i == 'DAT':

                    self.dat = True
                
                if i == 'FIN':

                    self.fin = True
                if i == 'RST':

                    #close client
                    sys.exit()


    
    def sendRestofTheFiles(self):
        #actually start sending request for files
        print(self.actual_total_files, ' ', self.dummy_total_files)
        if self.dummy_total_files>0:
            for file in range(0,self.actual_total_files):
                if self.actual_total_files - self.dummy_total_files == 1:
                    # print(self.expected_ack, self.bytes_received, self.total_bytes_received)
                    body = 'GET/'+self.read_files[file]+' HTTP/1.0'
                    packet = 'DAT|ACK|FIN'+'\n'+'Sequence: '+str(self.expected_ack)+'\n'+'Length: '+str(len(body))+'\n'+'Acknowledgement: '+str(self.total_bytes_received+1)+'\n'+'Windows: '+str(self.window_size)+'\r\n'+body
                    self.retransmission_queue.append(packet)
                    self.sender_queue.append('sending last file')
                    # print(packet,'just one file left')
                    self.transmit(packet) 
                    self.files_sent+=1
                    self.current_write_file = self.write_files[file]
                    self.write_files.pop(0)
                    self.total_bytes_sent += len(body)
                    self.expected_ack = self.total_bytes_sent+1
                    break
                elif self.actual_total_files - self.dummy_total_files !=1:
                    print('sending more than 2 files')
                    body = 'GET/'+self.read_files[file]+' HTTP/1.0'+'\n'+'Connection:keep-alive'
                    packet = 'DAT|ACK'+'\n'+'Sequence: '+str(self.expected_ack)+'\n'+'Length: '+str(len(body))+'\n'+'Acknowledgement: '+str(self.total_bytes_received+1)+'\n'+'Windows: '+str(self.window_size)+'\r\n'+body
                    self.retransmission_queue.append(packet)
                    self.sender_queue.append('sending last file')
                    self.transmit(packet)
                    self.files_sent+=1
                    self.current_write_file = self.write_files[0]
                    self.write_files.pop(0)
                    self.total_bytes_sent += len(body)
                    self.expected_ack = self.total_bytes_sent+1
                    break
                


        
    
    def ackCheckerConnection(self):
        #if ack is 1 it means send data
        packet=''
        print(self.ack_num_received, self.num_commands)
        if ((self.syn and self.ack) or self.ack) and self.ack_num_received == 1:
            self.retransmission_queue.pop(0)
            if self.persistent_connection:
                if self.dummy_total_files>0:
                    if self.dummy_total_files == self.actual_total_files:
                        self.ack_num =  1
                        body = 'GET/'+self.read_files[0]+'HTTP/1.0'+'\n'+'Connection:keep-alive'
                        packet = 'DAT|ACK'+'\n'+'Sequence: '+str(1)+'\n'+'Length: '+str(len(body))+'\n'+'Acknowledgement: '+str(self.ack_num)+'\n'+'Windows: '+str(self.window_size)+'\r\n'+body
                        self.retransmission_queue.append(packet)
                        self.sender_queue.append('sending First file')
                        self.transmit(packet)
                        self.total_bytes_sent +=len(body)
                        self.expected_ack = self.total_bytes_sent+1
                        self.start_reciveing_data = True
                        self.files_sent+=1
                        self.read_files.pop(0)
                        self.current_write_file = self.write_files[0]
                        self.write_files.pop(0)
                       

                            
                            
    def sendAcknowledgement(self):
        # print(str(self.seq+self.len), 'send acknowledgemnet')
        packet = 'ACK'+'\n'+'Sequence: '+str(self.expected_ack)+'\n'+'Length: '+str(0)+'\n'+'Acknowledgement: '+str(self.seq+self.len)+'\n'+'Windows: '+str(self.window_size)+'\r\n'
        self.retransmission_queue.append(packet)
        self.sender_queue.append('sending First file')
        print(packet)
        self.transmit(packet)
        pass

    def writeFile(self):
        self.file_packets_received = sorted(self.file_packets_received, key = lambda d: d['seq'])
        print('Writing in file')
        write_file = open(self.current_write_file, "w")
        for packet in range(0,len(self.file_packets_received)):
            print(len(self.file_packets_received))
            write_file.write(self.file_packets_received[packet]['content'])
        write_file.close()
        
    #only use from first data packet received
   
    def ackCheckerData(self,payload):
        self.extractBody(payload)
        print(self.ack_num_received,self.expected_ack)
        temp_dict = {}
        temp_dict['seq'],temp_dict['content-length'], temp_dict['content'] = 0,0,''
        if self.ack_num_received == self.expected_ack:
            #SYN|ACK|DAT SYN|ACK|DAT|FIN ACK|DAT|FIN ACK|DAT
            self.errorControl()
            if not self.error_encountered:
                # print(self.len, 'self.len')
                self.bytes_received += self.len
                if self.retransmission_queue:
                    self.retransmission_queue.pop()
                if self.dat and self.ack:
                    #if data flag is on
                    if self.start_reciveing_data:
                        # print('Bytes received',self.dummy_total_files,self.content_length, self.bytes_received,'\n\n') 
                        if self.bytes_received <=self.content_length:
                            print('entering after Bytes received',self.dummy_total_files,self.content_length, self.bytes_received,'\n\n') 
#                             print(self.body)
                            temp_dict['seq'],temp_dict['content-length'], temp_dict['content'] = self.seq, self.content_length, self.body
#                             print(temp_dict)
                            if len(self.file_packets_received)>0:
                                iteration_present = False
                                for i in self.file_packets_received:
                                    if i['seq'] == self.seq:
                                        iteration_present = True
                                if not iteration_present:
                                        self.file_packets_received.append(temp_dict)
                                        self.current_file_bytes += self.len
                                        self.sendAcknowledgement()
                            elif len(self.file_packets_received) == 0:
                                self.current_file_bytes += self.len
                                print('Adding first time')
                                self.file_packets_received.append(temp_dict)
                                self.sendAcknowledgement()
                            
                            # print('Bytes received',self.dummy_total_files,self.content_length,'self.len ',self.len, 'bytes',self.bytes_received, 'current', self.current_file_bytes)
                            if self.dummy_total_files != 1 and self.bytes_received == self.content_length:
                                print('multiple files')
                                self.dummy_total_files-=1
                                self.bytes_received = 0
                                
                                self.writeFile()
                                self.sendRestofTheFiles()
                            elif self.dummy_total_files == 1 and self.bytes_received == self.content_length:
                                self.dummy_total_files-=1
                                self.writeFile()
                                self.start_reciveing_data = False
                                #send FIN|ACK
                                sys.exit()
                    elif not self.start_reciveing_data:
                        #send last ack of and close
                        sys.exit()
                        
            elif self.error_encountered:
                print('error encountered')
                sys.exit()
                self.retransmit()

    def errorControl(self):
        if self.seq <= self.content_length:
            self.error_encountered = False
        elif self.seq > self.content_length:
            self.error_encountered = True

    def extractBody(self, payload):
        content = payload.decode('utf-8')
        print("extracting body")
        if self.body_at == 6:
            self.body = content.split('Windows: '+str(self.window_size_received)+'\r\n')[1]
            # print(self.body, 'body')
        elif self.body_at == 8:
            self.body = content.split(self.good_response+'\r\n')[1]
            # print(self.body,'body')
        elif self.body_at == 9:
            
            self.body = content.split(self.keep_alive+'\r\n')[1]
            # print(self.body,'body')
#             print(self.body)



   

    #remember all the 2nd packets  start coming from the command centre
    def commandCentre(self,payload):
        print('INSIDE COMMAND CENTER\n\n')
            #here everything will go down
        if self.syn and self.num_commands == 1:
            #syn
            self.retransmission_queue.pop(0)
            packet = 'ACK'+'\n'+'Sequence: '+str(0)+'\n'+'Length: '+str(0)+'\n'+'Acknowledgement: '+str(1)+'\n'+'Windows: '+str(0)
            self.sender_queue.append('Server')
            date_time = datetime.datetime.now().strftime("%a %d %b %H:%M:%S PDT %Y")
            self.retransmission_queue.append(packet)
            self.transmit(packet)
            print('COMMAND : SYN')
        elif self.ack and self.num_commands == 1:
            #maybe start receiving data?
         
            print('COMMAND : ACK')
            self.ackCheckerConnection()
        elif self.ack and self.syn and self.num_commands == 2:
            #maybe start receiving data?
         
            print('COMMAND : SYN|ACK')
            self.ackCheckerConnection()    
        elif self.ack and self.dat and self.num_commands == 2 :
            print('COMMAND : ACK|DAT')
            self.ack_dat = True
            self.start_receiving_data = True
            self.ackCheckerData(payload)
        elif self.syn and self.ack and self.dat and self.num_commands == 3:
            #straight data sending
            self.syn_ack_dat = True
            self.start_reciveing_data = True
            print('COMMAND : SYN|ACK|DAT')
            self.ackCheckerData(payload)
        elif self.syn and self.ack and self.dat and self.fin and self.num_commands == 4:
            self.syn_ack_dat_fin = True
            self.syn_start_receiving_data = True
            self.ackCheckerData(payload)
            # straight data sending
            print('COMMAND : SYN|ACK|DAT|FIN')
        elif self.ack and self.dat and self.fin and self.num_commands == 3:
            self.syn_start_receiving_data = True
            print('COMMAND : ACK|DAT|FIN')
            self.ackCheckerData(payload)
     
 
    def extractHeader(self,payload):
        content = payload.decode('utf-8')
        status = re.search('HTTP/1.0 200 OK\r\n',content)
        old_lines = content.splitlines()
        lines = list(filter(lambda element:element != '', old_lines))
        error_check = lines[1].split(':')[0]
        
        if len(lines)>5:
            if 'Content-length' == lines[5].split(':')[0]:
        
                if lines[6] == self.good_response:
                    print("good response")
                    self.commands = lines[0]
                    self.seq = int(lines[1].split(':')[1])
                    print(lines[2])
                    self.len = int(lines[2].split(':')[1]) 
                    print("self.len after received", self.len,'extract header\n\n')
                    self.ack_num_received = int(lines[3].split(':')[1])
                    self.window_size_received = int(lines[4].split(':')[1])
                    self.content_length = int(lines[5].split(':')[1])
                    self.total_bytes_received +=self.len
                    if self.persistent_connection:
                        self.keep_alive = lines[7]
                        self.body_at = 9
                    elif not self.persistent_connection:
                        self.body_at = 8
               
            elif self.good_response != lines[6]:
                print('average response')
                self.commands = lines[0]
                self.seq = int(lines[1].split(':')[1])
                self.len = int(lines[2].split(':')[1]) 
                self.ack_num_received = int(lines[3].split(':')[1])
                self.window_size_received = int(lines[4].split(':')[1])
                self.total_bytes_received +=self.len
                self.body_at = 6
                print(lines[2])
                print("self.len after received", self.len,'extract header\n\n')
        elif len(lines)<=5:
                self.commands = lines[0]
                self.body_at=6
                self.seq = int(lines[1].split(':')[1])
                self.len = int(lines[2].split(':')[1]) 
                self.ack_num_received = int(lines[3].split(':')[1])
                self.total_bytes_received += self.len
                self.window_size_received = int(lines[4].split(':')[1])

            
        elif 'Sequence' != error_check:
            print('ALERT WRONG HEADER RECEIVED')
            self.retransmit()


    #controls all the process after a payload received
    def receivedPayload(self, payload):
        self.extractHeader(payload)
        self.analyzeHeader()
        self.commandCentre(payload)


    def transmit(self, payload):
        print(self.server, 'Initiating transmission..')
        if self.sender_queue.pop(0):
            self.socket.sendto((payload).encode('utf-8'), (self.server))
            self.resetFlagsAfterSending()
            print('Transmitted')
    
    
    def retransmit(self):
        for i in self.retransmission_queue:
                self.socket.sendto(i.encode('utf-8'), self.server)



    def run(self):
        #first start reading from file
        self.actual_total_files = len(self.read_files)
        self.dummy_total_files = self.actual_total_files
        self.initConnection()


def startClientConnectionThread():
    host = sys.argv[1]
    port = int(sys.argv[2])
    client_Buffer = int(sys.argv[3])
    client_MSS = int(sys.argv[4])


    if len(sys.argv)>5:
        total_File_Couples = ((len(sys.argv)-5)/2)
        if total_File_Couples*2%2 == 0.0:
            print('here')
            counter = 0
            for i in range(0,int(total_File_Couples)):
                read_File_List.append(sys.argv[5+counter])
                write_File_List_.append(sys.argv[5+counter+1])
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
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(0)
    potential_reader = [sock]
    potential_writer = [sock]
    server = (host,port)
    count = 0
#     f = open('copy.txt', 'w')

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
                count= count+1
                clientData, clientAddress = sock.recvfrom(client_Buffer)
                print(clientData.decode('utf-8').splitlines()[1], ' Sequence\n\n')
                client_online.receivedPayload(clientData)
                potential_writer.append(sock)

            if not (readable or writable or exceptional):
                print('timeout')
#                 f.close()
#                 sys.exit()
                client_online.retransmit()
                potential_writer.append(sock)

    except IOError:
        print('keyboard interrupt, exiting')
    sock.close()
# python3 sor-client.py 134.87.131.31 80 8120 512 dumm01.txt copy01.txt dummy02.txt copy02.txt dummy03.txt copy03.txt

if __name__ == '__main__':
    startClientConnection = threading.Thread(target = startClientConnectionThread())
    startClientConnection.start()

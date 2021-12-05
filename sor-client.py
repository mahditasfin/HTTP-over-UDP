from os import read
import socket, threading, selectors, sys, select

#create packeting which can be used in the server code
#initiate client connection
sel = selectors.DefaultSelector()
read_File_List = []
write_File_List_= []
client_packets=[]
messages = [b"GET/sws.py/HTTP/1.0"]





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


def createPackets():
    packet=''
    if len(read_File_List)>1:
        for i in range(0,len(read_File_List)):
            #for packet no 1
            if i == 0:
                packet = 'SYN|DAT|ACK'+'\n'+'Sequence'+str(0)+'\n'+'Length'+str(0)+'\n'+'Acknowledgement:'+str(0)+'\n'+'Windows:'+str(4096)+'\n\n'+'GET/'+read_File_List[i]+' HTTP/1.0'+'\n'+'Connection:keep-alive'
                client_packets.append(packet)
            #for last packet
            elif i == len(read_File_List)-1:
                packet= 'ACK|DAT|FIN'+'\n'+'Sequence'+str(0)+'\n'+'Length'+str(0)+'\n'+'Acknowledgement:'+str(0)+'\n'+'Windows:'+str(4096)+'\n\n'+'GET/'+read_File_List[i]+' HTTP/1.0'+'\n'
                client_packets.append(packet)
            #for rest packet
            else:
                packet = 'DAT|ACK'+'\n'+'Sequence'+str(0)+'\n'+'Length'+str(0)+'\n'+'Acknowledgement:'+str(0)+'\n'+'Windows:'+str(4096)+'\n\n'+'GET/'+read_File_List[i]+' HTTP/1.0'+'\n'+'Connection:keep-alive'
                client_packets.append(packet)
    for i in client_packets:
        print(i,'\n\n')

def startClientConnectionThread():
    host = str(sys.argv[1])
    port = int(sys.argv[2])
    client_Buffer = int(sys.argv[3])
    server_MSS = int(sys.argv[4])


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
            print("Inconsisten read and write file combination")
            sys.exit()
    print(read_File_List,write_File_List_)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(0)
    potential_reader = [sock]
    potential_writer = [sock]
    createPackets()
    try:
        while True:
            readable, writable, exceptional = select.select(potential_reader, potential_writer, potential_reader,2)
            if sock in writable:
                potential_writer.remove(sock)


            #analyze payload command
            if sock in readable:
                counter= counter+1
                clientData, clientAddress = sock.recvfrom(2048)
                analyzeReceivedPayload(clientData)
                potential_writer.append(sock)

            if not (readable or writable or exceptional):
                potential_writer.append(sock)

    except IOError:
        print('keyboard interrupt, exiting')
    sock.close()


if __name__ == '__main__':
    startClientConnection = threading.Thread(target = startClientConnectionThread())
    startClientConnection.start()

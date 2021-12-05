import os, math ,sys, datetime, socket, logging, threading, select, json, re
init_Connection = True

class UDPjointServerClient(object):
    def __init__(self, inputFile, outputFile, payload, lsock):
        self.sock = lsock
        self.HEADER_LENGTH = 20
        self.current_file_queue = []
        self.file = ''
        self.keep_track = 1
        #sender variables
        self.inputFile = inputFile
        self.total_packets_left = 0
        self.initial_expected_ack = 1
        self.expected_ack = 0
        self.start_Connection = False
        self.sender_command = ''
        self.syn = 0
        self.seq = 0
        self.len = 0
        self.MSS = 1024
        self.window_sender = 5120
        self.file_Size = os.path.getsize(self.inputFile)
        self.expected_acks = []
        self.last_ack_received = 0
        self.terminating_ack= 0
        self.total_bytes_sent = 0
        self.data_packets = []
        self.ready_packets = []
        self.sender_payload = {}
        self.retransmission_counter = 0
        self.retransmission_queue = []
        #receiver variables
        self.end_connection = False
        self.track_receiver_packets = []
        self.initial_packet_tracker = 1
        self.concat_check = False
        self.corrupted_payload = ''
        self.receiver_command = ''
        self.ack = 1
        self.window = 5120
        self.window_receiver = 5120
        self.receiver_packet_count = 1
        self.window_sender = 5120
        self.last_Command_Receiver = ''
        self.last_Command_Sender = ''
        self.total_bytes_received = ''
        self.output_File = outputFile
        self.receiver_payload = {}
        #readable variables
        self.payload = payload

        #for sending
        self.senderQueue=[]



        #return packets
        #calculate expected acks


    def initjsonObject(self,readerOrSender):
        jsonObject = {}
        if readerOrSender == 'receiver':
            jsonObject['header'], jsonObject['body'] ={},{}
            jsonObject['header']['comm'],jsonObject['header']['ack'],jsonObject['header']['win']='', 0,0

        if readerOrSender == 'sender':
            jsonObject['header'], jsonObject['body'] ={},{}
            jsonObject['header']['comm'],jsonObject['header']['seq'],jsonObject['header']['len']='',0,0

        return jsonObject


    def formatSenderPayload(self, comm, seq, len, body):
        self.sender_payload['header']['comm'] = comm
        self.sender_payload['header']['seq'] = seq
        self.sender_payload['header']['len'] = len

        if body:
            self.sender_payload['body'] = body




    def formatReceiverPayload(self, comm, ack, window):
        self.receiver_payload['header']['comm'] = comm
        self.receiver_payload['header']['ack'] = ack
        self.receiver_payload['header']['win'] = window

    def updateExpectedAck(self):
        #here the expected ack will get updated with the len it's sending
        self.expected_ack = self.len + 1
        pass

    def createPackets(self):
        if self.file_Size > 0:
            with open(self.inputFile,'rb') as f:
                data = f.read(self.MSS)
                self.data_packets.append(data)
                while len(data) != 0:
                    data =f.read(self.MSS)
                    self.data_packets.append(data)
        self.total_packets_left = len(self.data_packets)



    def start_sending_data(self):
        self.sender_command='DAT'
        if self.total_packets_left <= math.floor(self.window_sender/self.MSS):
            for i in range(0, len(self.ready_packets)):
                self.retransmission_queue.append(self.ready_packets[0])
                self.current_file_queue.append(self.ready_packets.pop(0))
                self.total_packets_left = self.total_packets_left-1
        elif self.total_packets_left > math.floor(self.window_sender/self.MSS):
            packets_can_be_sent = math.floor(self.window_sender/self.MSS)
            for i in range(0,packets_can_be_sent):
                for i in self.ready_packets:
                    if i['packetNo'] == self.keep_track:
                        self.retransmission_queue.append(self.ready_packets[0])
                        self.current_file_queue.append(self.ready_packets.pop(0))
                        self.keep_track= self.keep_track+1
                        self.total_packets_left = self.total_packets_left-1


    def startPacketing(self):
        for i in self.data_packets:
            sender_payload = {}
            sender_payload['header'] = {}
            sender_payload['header']['comm']='DAT'
            sender_payload['header']['seq']=self.total_bytes_sent+1
            sender_payload['header']['len']=len(i.decode('utf-8'))
            sender_payload['body'] = i.decode('utf-8')
            sender_payload['packetNo'] = self.data_packets.index(i)+1
            self.total_bytes_sent+=len(i)

            #expected acks are created too at the same time
            self.expected_acks.append(self.total_bytes_sent+1)

            self.ready_packets.append(sender_payload)

        self.terminating_ack = self.expected_acks.pop(-1)



    def updateSender(self):
        self.receiver_payload = self.payload
        self.sender_command = self.receiver_payload['header']['comm']


        if self.sender_command:
            if self.sender_command == 'ACK':
                if self.receiver_payload['header']['ack'] == self.initial_expected_ack:
                    self.retransmission_queue.pop(0)
                    self.last_ack_received = self.receiver_payload['header']['ack']
                    self.initial_expected_ack = 0
                    self.window_sender = self.receiver_payload['header']['win']
                    self.start_sending_data()
                elif self.file_Size+2 == self.receiver_payload['header']['ack']:
                    sys.exit()
                elif len(self.expected_acks)>0:
                       if self.receiver_payload['header']['ack'] == self.expected_acks[0]:
                        self.expected_acks.pop(0)
                        self.last_ack_received = self.receiver_payload['header']['ack']
                        self.window_sender = self.receiver_payload['header']['win']
                        self.retransmission_queue.pop(0)
                        if len(self.ready_packets)>0:
                            self.start_sending_data()
#                         if len(self.expected_acks) == 0:
#                             self.sender_command = 'FIN'
                elif self.receiver_payload['header']['ack'] == self.last_ack_received:
                    self.retransmission_counter = self.retransmission_counter+1
                    if self.retransmission_counter == 3:
                        self.retransmit()




    def readabletriggered(self, payload):
        payload = payload.decode('utf-8')
        self.payload = json.loads(payload)

        comm = self.payload['header']['comm']

        #heart of the system:
        if comm == 'SYN':
            date_time = datetime.datetime.now().strftime("%a %d %b %H:%M:%S PDT %Y")
            print(date_time+':','Receive;',comm+';','Sequence:',str(self.payload['header']['seq'])+';','Length:',str(self.payload['header']['len']))
            self.updateReceiver()
        elif comm == 'ACK':
            date_time = datetime.datetime.now().strftime("%a %d %b %H:%M:%S PDT %Y")
            print(date_time+':','Receive;','ACK;','Acknowledgement:',str(self.payload['header']['ack'])+';','Window:',str(self.payload['header']['win']))
            self.updateSender()
        elif comm == 'DAT':
            date_time = datetime.datetime.now().strftime("%a %d %b %H:%M:%S PDT %Y")
            print(date_time+':','Receive;',comm+';','Sequence:',str(self.payload['header']['seq'])+';','Length:',str(self.payload['header']['len']))
            self.updateReceiver()
        elif comm == 'FIN':
            date_time = datetime.datetime.now().strftime("%a %d %b %H:%M:%S PDT %Y")
            print(date_time+':','Receive;',comm+';','Sequence:',str(self.payload['header']['seq'])+';','Length:',str(self.payload['header']['len']))
            self.updateReceiver()

        elif comm == 'RST':
            self.updateSender()


    def writeInFile(self):
        for i in self.track_receiver_packets:
            self.file.write(i['body'])
        self.file.close()

    def concatCheck(self):
        if self.sender_payload:
            isConcat = len(re.findall('["]packetNo["][:]', json.dumps(self.sender_payload)))
        if isConcat>1:
            self.concat_check = True


    def updateReceiver(self):
        self.sender_payload = self.payload
        self.receiver_command = self.sender_payload['header']['comm']
        if self.receiver_command:
            if self.receiver_command == 'SYN':
                self.receiver_command = 'ACK'
            elif self.receiver_command == 'DAT':
                self.concatCheck()
                if self.sender_payload["packetNo"]:
                    dummy_object = {
                        'ack': self.sender_payload['header']['seq']+self.sender_payload['header']['len'],
                        'packetIndex': self.sender_payload["packetNo"],
                        'body': self.sender_payload['body']
                    }
                    iteration_present = False
                    for i in self.track_receiver_packets:
                        if i['packetIndex'] == dummy_object['packetIndex']:
                            iteration_present= True
                    if not iteration_present:
                        self.track_receiver_packets.append(dummy_object)
                    if self.track_receiver_packets and len(self.track_receiver_packets)>1:
                        self.track_receiver_packets = sorted(self.track_receiver_packets, key = lambda d: d['packetIndex'])
                        contains_next = self.check_next()
                        if contains_next != 0:
                            self.ack = self.track_receiver_packets[contains_next]['ack']
                            self.initial_packet_tracker = self.initial_packet_tracker+1
                    elif self.sender_payload["packetNo"] == self.initial_packet_tracker:
                        self.ack = self.sender_payload['header']['seq']+self.sender_payload['header']['len']
                        self.initial_packet_tracker = self.initial_packet_tracker+1
                    self.window_receiver = self.window-self.MSS
                    self.receiver_command = 'ACK'
                    self.receiver_packet_count = self.receiver_packet_count+1





    def check_next(self):
        for i in range(0,len(self.track_receiver_packets)):
            if self.track_receiver_packets[i]['packetIndex'] == self.initial_packet_tracker:
                return i
        return 0


    def checkReceiver(self):
        if self.receiver_command == 'ACK':
            self.formatReceiverPayload(self.receiver_command, self.ack, self.window_receiver)
            self.senderQueue.append('Receiver')
            date_time = datetime.datetime.now().strftime("%a %d %b %H:%M:%S PDT %Y")
            print(date_time+':','Send;','ACK;','Acknowledgement:',str(self.ack)+';','Window:',str(self.receiver_payload['header']['win']))
            self.transmit(self.receiver_payload)
            self.receiver_command = ''
        elif self.receiver_command == 'FIN' and not self.end_connection:
            self.end_connection = True
            #write here
            self.writeInFile()
            self.formatReceiverPayload('ACK',self.file_Size+2, self.window_receiver)
            date_time = datetime.datetime.now().strftime("%a %d %b %H:%M:%S PDT %Y")
            print(date_time+':','Send;','ACK;','Acknowledgement:',str(self.file_Size+2)+';','Window:',str(self.receiver_payload['header']['win']))
            self.senderQueue.append('Receiver')
            self.transmit(self.receiver_payload)



    def checkSender(self):
        if self.sender_command == 'DAT':
            for i in range(0,len(self.current_file_queue)):
                self.senderQueue.append('Sender')
                date_time = datetime.datetime.now().strftime("%a %d %b %H:%M:%S PDT %Y")
                if self.current_file_queue[0]['header']['seq'] == self.file_Size+1:
                    self.current_file_queue[0]['header']['comm'] = 'FIN'
                print(date_time+':','Send;',self.current_file_queue[0]['header']['comm']+';Sequence:'+str(self.current_file_queue[0]['header']['seq'])+';','Length:',str(self.current_file_queue[0]['header']['len']))
                self.transmit(self.current_file_queue.pop(0))
        elif self.sender_command == 'FIN':
            self.senderQueue.append('Sender')
            self.formatSenderPayload(self.sender_command, self.total_bytes_sent+1, 0, '')
            self.sender_payload['body'] = ''
            self.transmit(self.sender_payload)


    def writabaletriggered(self):
        if self.start_Connection:
            #needs to send SYN
            self.sender_command = 'SYN'
            self.formatSenderPayload(self.sender_command,self.seq,self.len,'')
            self.senderQueue.append('Sender')
            date_time = datetime.datetime.now().strftime("%a %d %b %H:%M:%S PDT %Y")
            print(date_time+',Send;',self.sender_command+';','Sequence:',str(self.seq),';Length:',str(self.len))
            self.retransmission_queue.append(self.sender_payload)
            self.transmit(self.sender_payload)
            self.start_Connection = False
        self.checkSender()
        self.checkReceiver()



    def transmit(self, payload):
        echo_port = ('10.10.1.100', 8888)
        if self.senderQueue.pop(0):
            self.sock.sendto(json.dumps(payload).encode('utf-8'), echo_port)



    def retransmit(self):
        echo_port = ('10.10.1.100', 8888)
        self.senderQueue.append('Sender')
        for i in self.retransmission_queue:
            if self.last_ack_received == i['header']['seq']:
                self.sock.sendto(json.dumps(i).encode('utf-8'), echo_port)





    def setup(self):
        if init_Connection:
            self.start_Connection = True
            self.file = open("copy.txt", "w")
            self.receiver_payload = self.initjsonObject('receiver')
            self.sender_payload = self.initjsonObject('sender')
            self.createPackets()
            self.startPacketing()
        #setUp everything


def checkCorruptedPayload(payload):
    corrupted_payload = payload.decode('utf-8')
    extract_packet = re.search('["]DAT["]',corrupted_payload)
    if extract_packet:
        isCorrupted = [m.start() for m in re.finditer('["]body["][:]', corrupted_payload)]
        if len(isCorrupted) != 1:
            return False
    return True

def startConnectionThread():
    host = str(sys.argv[1])
    port = int(sys.argv[2])
    readFile = str(sys.argv[3])
    writeFile = str(sys.argv[4])

    logger = logging.getLogger()

    #setup socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(0)
    sock.bind((host,port))
    potential_reader = [sock]
    potential_writer = [sock]



    if init_Connection:
        jointClientServer = UDPjointServerClient(readFile,writeFile,b'',sock)
        jointClientServer.setup()

    counter = 1
    try:
        while True:
            readable, writable, exceptional = select.select(potential_reader, potential_writer, potential_reader,2)
            if sock in writable:
                jointClientServer.writabaletriggered()
                potential_writer.remove(sock)


            if sock in readable:
                counter= counter+1
                clientData, clientAddress = sock.recvfrom(2048)
                clientData_not_corrupted = checkCorruptedPayload(clientData)
                if clientData_not_corrupted:
                    jointClientServer.readabletriggered(clientData)
                    potential_writer.append(sock)

            if not (readable or writable or exceptional):
                potential_writer.append(sock)
                jointClientServer.retransmit()

    except IOError:
        print('keyboard interrupt, exiting')
    sock.close()


if __name__ == '__main__':

    #starting thread which will start class

    startConnection = threading.Thread(target=startConnectionThread())
    startConnection.start()

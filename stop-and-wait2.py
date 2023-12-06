import socket
from datetime import datetime

# total packet size
PACKET_SIZE = 1024
# bytes reserved for sequence id
SEQ_ID_SIZE = 4
# bytes available for message
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE

# total delay of all packets in seconds
total_delay = 0

# number of packets sent total
packet_number = 0

# read data
with open('file.mp3', 'rb') as f:
    data = f.read()
 
# create a udp socket
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:

    # bind the socket to a OS port
    udp_socket.bind(('0.0.0.0', 5000))
    udp_socket.settimeout(1)
    socket_opened_time = datetime.now()

    # start sending data from 0th sequence
    seq_id = 0
    while seq_id < len(data):
        
        # construct message
        # sequence id of length SEQ_ID_SIZE + message of remaining PACKET_SIZE - SEQ_ID_SIZE bytes
        message = int.to_bytes(seq_id, SEQ_ID_SIZE, signed=True, byteorder='big') + data[seq_id : seq_id + MESSAGE_SIZE]
        
        data_length = len(data[seq_id : seq_id + MESSAGE_SIZE])

        packet_number += 1
        sendtime = datetime.now()

        # send message out
        udp_socket.sendto(message, ('localhost', 5001))
        
        # wait for acknowledgement
        while True:
            try:
                # wait for ack
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                
                # extract ack id
                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big')
                print(ack_id, ack[SEQ_ID_SIZE:])
                
                # ack id == next sequence id, move on
                if ack_id == seq_id + data_length:
                    recvtime = datetime.now()
                    delta = recvtime - sendtime
                    total_delay += delta.total_seconds()
                    break
            except socket.timeout:
                # no ack, resend message
                udp_socket.sendto(message, ('localhost', 5001))
                
        # move sequence id forward
        seq_id += data_length

    # send empty final closing message
    udp_socket.sendto(int.to_bytes(seq_id, SEQ_ID_SIZE, signed=True, byteorder='big'), ('localhost', 5001))
    
    while True:
            try:
                # wait for ack
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                
                # extract ack id
                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big')
                print(ack_id, ack[SEQ_ID_SIZE:])
                
                # ack id == next sequence id, move on
                if ack_id == seq_id:
                    recvtime = datetime.now()
                    delta = recvtime - sendtime
                    total_delay += delta.total_seconds()
                    break
            except socket.timeout:
                # no ack, resend message
                udp_socket.sendto(message, ('localhost', 5001))
    
    # Send final message for receiver to exit
    udp_socket.sendto(int.to_bytes(seq_id, SEQ_ID_SIZE, signed=True, byteorder='big') + bytes("==FINACK==", "utf-8"), ('localhost', 5001))

    all_acks_recvtime = datetime.now()
    delta = all_acks_recvtime - socket_opened_time
    throughput = len(data) / delta.total_seconds()

    avg_delay = total_delay/packet_number

    print("Average Per-Packet Delay: ", avg_delay, " seconds")
    print("Throughput: ", throughput, " bytes/second")
    print("Throughput / Avg. Delay Metric: ", throughput/avg_delay)
import socket
from datetime import datetime
import math

# total packet size
PACKET_SIZE = 1024
# bytes reserved for sequence id
SEQ_ID_SIZE = 4
# bytes available for message
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE



# TCP Tahoe related variables
# The maximum amount of acknowledgements allowed before multiple acks is detected.
MULTIPLE_ACK_COUNT = 3
# Current window size in number of packets
# This is a dynamic variable that can change at runtime.
cWindowSize = 1
# The potenitally dynamic slow start threshold.
ssThresh = 64
# The current state of the protocol.
# Commented out for TCP Tahoe and Reno, as the states for these can be
# deduced from size of cWindowSize, but perhaps cubic will want to do something
# unique....

# state = "slow_start" # Can either be "slow_start", "cong_avoid", or "fast_rec"

# TCP Cubic++ related variables
# These are constants used in A
C = 0.4
BETA = 0.7

# window size right before the last reduction
wmax = 1
# time that has elapsed since last reduction (in seconds)
time_since_reduction = 0
# packet number (reset to 0 after a reduction)
packet_num = 0
# sum of packet delays in the current period (reset to 0 after a reduction)
rtt_total = 0
# the average RTT of the packets since the last reduction (calculated after a reduction)
rtt_avg = 1
# linear factor calculated by 1/(10*rtt_avg)
ඞ = 0.1

reduction_time = datetime.now()

# read data
with open('file.mp3', 'rb') as f:
    data = f.read()

def construct_packet(seq_id):
    data_segment = data[seq_id : seq_id + MESSAGE_SIZE]
            
    # make sure to pad out the message with 0s if it's not the full size
    if len(data_segment) < MESSAGE_SIZE:
        data_segment += b'\0' * (MESSAGE_SIZE - len(data_segment))
    
    # construct message and add it to list
    message = int.to_bytes(seq_id, SEQ_ID_SIZE, signed=True,byteorder='big') + data_segment
    return message
 

# total delay of all packets in seconds
total_delay = 0

packets_in_window = {}

send_times = {}

recvtimes = {}

window_offset = 0

most_recent_ack = 0

last_ack_id = -1
second_last_ack_id = -2

# create a udp socket
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:

    # bind the socket to a OS port
    udp_socket.bind(('0.0.0.0', 5000))
    udp_socket.settimeout(1)
    socket_opened_time = datetime.now()
    
    # Populates the packets_in_window
    def update_window():
        global window_offset
        global packets_in_window
        # add packets that are in the window but not in the dictionary

        # print(f"window size : {cWindowSize}")

        for i in range(int(cWindowSize)):
            if window_offset + i * MESSAGE_SIZE >= len(data):
                break
            seq_id = window_offset + i * MESSAGE_SIZE
            if(packets_in_window.get(seq_id) == None):
                packets_in_window[seq_id] = [construct_packet(seq_id), False] # (message, if acked)
        # remove packets that are no longer in the window
        seq_ids = list(packets_in_window.keys())
        for seq_id in seq_ids:
            if seq_id < window_offset or seq_id >= window_offset + cWindowSize * MESSAGE_SIZE:
                packets_in_window.pop(seq_id)

    def send_unacked_packets():
        global window_offset
        global packets_in_window
        global packet_num
        global send_times

        now = datetime.now()

        for seq_id, [message, acked] in packets_in_window.items():
            if acked:
                # ignore acknowledged packets
                continue
            # if sending packet for the first time, record the time
            if send_times.get(seq_id) == None:
                send_times[seq_id] = now
            # send packet
            udp_socket.sendto(message, ('localhost', 5001))
            packet_num += 1
            # print("Sending message with seq_id: ", seq_id)
                    
    # cumuliative acknowldgement: acknowledge all packets < ack_id
    def cuml_ack(ack_id):
        global window_offset
        global packets_in_window
        global rtt_total
        global recvtimes
        global send_times
        
        now = datetime.now()
        # window_offset, window_offset + MESSAGE_SIZE, window_offset + 2*MESSAGE_SIZE ..., ack_id - MESSAGE_SIZE
        # print("Cumulative ack: ", window_offset, ack_id)
        for seq_id in range(window_offset, ack_id, MESSAGE_SIZE):
            packets_in_window[seq_id][1] = True
            recvtimes[seq_id] = now
            delta = recvtimes[seq_id] - send_times[seq_id]
            rtt_total += delta.total_seconds()
        window_offset = ack_id

    # Set the size of the congestion window. This automatically
    # determines the size of the increas based on what state the
    # congestion control protocol is in (slow start, congestion avoid)
    def adjust_cWindow_size():
        global cWindowSize
        global ssThresh
        global wmax
        global reduction_time
        global K
        global BETA
        global C
        global ඞ

        TMP_DEBUG_cWindowSize = cWindowSize

        if cWindowSize < ssThresh:
            # slow start
            cWindowSize *= 2
        else:
            # congestion avoid
            delta = datetime.now() - reduction_time
            time_since_reduction = delta.total_seconds()
            K = math.pow((wmax * (1-BETA))/C, 1/3)
            cWindowSize = C * math.pow(time_since_reduction - K, 3) + wmax
            cWindowSize += ඞ
            cWindowSize = max(int(cWindowSize), 1)

        # print(f"windowChange: {TMP_DEBUG_cWindowSize} -> {cWindowSize}")
        
        # commented implementation involving states.
        # global state
        # if state == "slow_start":
            # ...
        # elif state == "cong_avoid":
            # ...
        # elif state == "fast_rec"
            # ...
    
    # When encountering either a double acknowledgement or a timeout,
    # call control_congestion() to resize ssThresh and cWindowSize
    # context should be either "double_dup" or "timeout"
    # Essentially the same as TCP Tahoe, but use this for the congestion_control()
    # function instead.
    def control_congestion(context):
        # print("Congestion control called with context: ", context)
        global cWindowSize
        global ssThresh
        global wmax
        global reduction_time
        global K
        global BETA
        global C
        global ඞ
        global packet_num
        global rtt_total

        ssThresh = max(cWindowSize / 2, 1)

        wmax = cWindowSize

        reduction_time = datetime.now()
        
        rtt_avg = rtt_total / max(packet_num, 1)

        if(rtt_avg == 0): ඞ = 0
        else: ඞ = 1/(10 * rtt_avg)

        rtt_total = 0
        packet_num = 0

        if context == "double_dup":
            cWindowSize = ssThresh
        elif context == "timeout":
            cWindowSize = 1

    while window_offset < len(data):
        update_window()
        send_unacked_packets()
        recieved_ack = False
        last_ack_id = -1
        second_last_ack_id = -2
        while True:
            try:
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                
                recieved_ack = True

                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big')


                # print(ack_id, ack[SEQ_ID_SIZE:])

                # if acknowledgement is beyond window, entire window is
                # accepted.
                
                if ack_id > window_offset + cWindowSize * MESSAGE_SIZE:
                    cuml_ack(ack_id)                    
                    break
                cuml_ack(ack_id)

                if(ack_id == second_last_ack_id and ack_id == last_ack_id):
                    # triple ack    
                    control_congestion("double_dup")
                    break
                # elif (ack_id == second_last_ack_id or last_ack_id == second_last_ack_id or ack_id == last_ack_id):
                    # print(f"Found a repeat in acknowledgements: {ack_id} <- {last_ack_id} <- {second_last_ack_id}")
                
                second_last_ack_id = last_ack_id
                last_ack_id = ack_id
                
            except:
                # update_window()
                # send_unacked_packets()
                break

        if not recieved_ack:
            control_congestion("timeout")
                    
        # increease cWindowSize. Should automatically detect the
        # state for Tahoe and Reno.
        adjust_cWindow_size()
    
    # send empty final closing message
    sendtime = datetime.now()
    last_seq_id = last_ack_id
    # print("Sending final message with seq_id: ", last_seq_id)
    udp_socket.sendto(int.to_bytes(last_seq_id, SEQ_ID_SIZE, signed=True, byteorder='big'), ('localhost', 5001))
    
    while True:
            try:
                # wait for ack
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                
                # extract ack id
                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big')
                # print(ack_id, ack[SEQ_ID_SIZE:])
                
                # ack id == next sequence id, move on
                if ack_id == last_seq_id:
                    recvtime = datetime.now()
                    delta = recvtime - sendtime
                    total_delay += delta.total_seconds()
                    break
            except socket.timeout:
                # no ack, resend message
                udp_socket.sendto(int.to_bytes(last_seq_id, SEQ_ID_SIZE, signed=True, byteorder='big'), ('localhost', 5001))
    
    # Send final message for receiver to exit
    udp_socket.sendto(int.to_bytes(last_seq_id, SEQ_ID_SIZE, signed=True, byteorder='big') + bytes("==FINACK==", "utf-8"), ('localhost', 5001))

    all_acks_recvtime = datetime.now()

    for seq_id, sendtime in send_times.items():
        # print(f"{seq_id},{sendtime}, {recvtimes[seq_id]}")
        delta = recvtimes[seq_id] - sendtime
        total_delay += delta.total_seconds()

    delta = all_acks_recvtime - socket_opened_time
    throughput = len(data) / delta.total_seconds()

    packet_number = (len(data) + MESSAGE_SIZE - 1) / MESSAGE_SIZE
    avg_delay = total_delay/packet_number

    # print("Average Per-Packet Delay: ", avg_delay, " seconds")
    # print("Throughput: ", throughput, " bytes/second")
    # print("Throughput / Avg. Delay Metric: ", throughput/avg_delay)

    print(f"{round(throughput, 2)},{round(avg_delay, 2)},{round(throughput/avg_delay, 2)}")

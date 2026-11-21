"""Chapter 11 spike 1b: where do the seconds of a new connection go? Times the four phases of a new HTTPS connection
(name lookup, TCP connect, TLS handshake, first response) to one host, every `pause` seconds.

    python docs/ch11/spike/measure_phases.py api.open-meteo.com 12 10

Run for both hosts in parallel, 12 trials 10 s apart, on the development laptop on 22 Nov 2026; the output is
docs/ch11/data/connection_phases.csv. Result: the name lookup took 3.05 to 3.09 s in 21 of 24 trials (1.06 to 1.07 s
in the other 3); TCP, TLS and the response never took more than 0.22 s each.
"""
import socket, ssl, time, sys
host = sys.argv[1]
ctx = ssl.create_default_context()
for i in range(int(sys.argv[2])):
    t0 = time.perf_counter()
    ai = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    t1 = time.perf_counter()
    s = socket.create_connection((host, 443), timeout=10)
    t2 = time.perf_counter()
    w = ctx.wrap_socket(s, server_hostname=host)
    t3 = time.perf_counter()
    w.sendall(f"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode())
    w.recv(200)
    t4 = time.perf_counter()
    w.close()
    print(f"{host[:12]} run{i} dns={1000*(t1-t0):.0f} tcp={1000*(t2-t1):.0f} tls={1000*(t3-t2):.0f} resp={1000*(t4-t3):.0f}", flush=True)
    time.sleep(float(sys.argv[3]))

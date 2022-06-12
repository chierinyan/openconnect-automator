FROM debian

RUN apt-get update && \
    apt-get install -y ca-certificates openconnect python3-pip iptables curl && \
    apt-get clean
RUN update-ca-certificates
RUN pip3 install "vpn-slice[dnspython,setproctitle]"

COPY init.py /init.py
CMD ["/usr/bin/python3", "/init.py"]

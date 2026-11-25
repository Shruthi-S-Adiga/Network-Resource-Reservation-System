"""Optional custom Mininet topology: 3 hosts and one OpenFlow switch."""
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel

class ReservationTopo(Topo):
    def build(self):
        s1 = self.addSwitch("s1", protocols="OpenFlow13")
        h1 = self.addHost("h1", ip="10.0.0.1/24")
        h2 = self.addHost("h2", ip="10.0.0.2/24")
        h3 = self.addHost("h3", ip="10.0.0.3/24")
        self.addLink(h1, s1, cls=TCLink, bw=100)
        self.addLink(h2, s1, cls=TCLink, bw=100)
        self.addLink(h3, s1, cls=TCLink, bw=100)

def run():
    topo = ReservationTopo()
    net = Mininet(topo=topo, controller=None, switch=OVSSwitch, link=TCLink, autoSetMacs=True)
    net.addController("c0", controller=RemoteController, ip="127.0.0.1", port=6653)
    net.start()
    print("Hosts: h1=10.0.0.1, h2=10.0.0.2, h3=10.0.0.3")
    print("Try: pingall; h1 ping -c 3 10.0.0.2")
    CLI(net)
    net.stop()

if __name__ == "__main__":
    setLogLevel("info")
    run()

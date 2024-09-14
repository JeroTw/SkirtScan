import asyncio
import aiohttp
import ipaddress
import socket
import numpy as np
import threading
import random
import string
import argparse
from tqdm import tqdm

parser = argparse.ArgumentParser()
parser.add_argument('-t', '--threads', help='threads count', required=True, default=1000)
parser.add_argument('-c', '--country', help='country code', required=True)
parser.add_argument('-p', '--ports', help='ports (25-100) or (25)', required=True)
args = parser.parse_args()

slice_count = int(args.threads)
total_ips = 0

async def get_country_cidr(country_code):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://raw.githubusercontent.com/herrbischoff/country-ip-blocks/master/ipv4/{country_code}.cidr"
        ) as response:
            return await response.text()
    
async def parse_cidr(cidr_list):
  all_ip_addresses = []
  for cidr in cidr_list.split('\n'):
    if not cidr:
        continue
    network = ipaddress.ip_network(cidr.strip()) 
    all_ip_addresses.extend([str(ip) for ip in network])
  return all_ip_addresses


def scan_thread(ips, ports, pbar): 
    global total_ips
    for ip in ips:
        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.connect((ip, int(port)))
                results.append((ip, int(port)))
            except Exception as error:
                pass
        total_ips += 1
        pbar.update(1) 

async def start_scan(sid, country, ports):
    global forscan
    forscan = 0
    global results
    results = []
    ips = await parse_cidr(await get_country_cidr(country))
    forscan = len(ips)
    ips = np.array_split(ips, slice_count)
    threads = []
    with tqdm(total=forscan, desc="Scanning IPs", bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]") as pbar:
        for i in ips:
            thread = threading.Thread(target=scan_thread, args=(i, ports, pbar)) 
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
    print(f"Total found: {len(results)}")
    for line in results:
        open(f'results_{country}_{ports}_{sid}.txt', 'a').write(f"{line[0]}:{line[1]}\n")
    print(f"Results saved to results_{country}_{ports}_{sid}.txt")



def get_random_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

asyncio.new_event_loop().run_until_complete(start_scan(get_random_id(), args.country.lower(), args.ports.split(',')))

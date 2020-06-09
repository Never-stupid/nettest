#!/usr/bin/env python
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import threading
import sys
import subprocess
from urllib.parse import parse_qs, urlparse
import logging
import os
import json

def locate(file):
    #Find the path for fping or trace
    for path in os.environ["PATH"].split(os.pathsep):
        if os.path.exists(os.path.join(path, file)):
                return os.path.join(path, file)
    return "{}".format(file)

def ping(host, prot, interval, count, size, source):
    # Using source address?
    if source == '':
        ping_command = '{} -{} -b {} -i 1 -p {} -q -c {} {}'.format(filepath['ping'], prot, size, interval, count, host)
    else:
        ping_command = '{} -{} -b {} -i 1 -p {} -q -c {} -S {} {}'.format(filepath['ping'], prot, size, interval, count, source, host)

    output = []
    #Log the actual ping command for debug purpose
    #Execute the ping
    cmd_output = subprocess.Popen(ping_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
    #Parse the fping output
    try:
        loss = cmd_output[1].decode().split("%")[1].split("/")[2]
        min = cmd_output[1].decode().split("=")[2].split("/")[0]
        avg = cmd_output[1].decode().split("=")[2].split("/")[1]
        max = cmd_output[1].decode().split("=")[2].split("/")[2].split("\n")[0]
    except IndexError:
        loss = 100
        min = 0
        avg = 0
        max = 0
    #Prepare the metric
    output.append("ping_avg {}".format(avg))
    output.append("ping_max {}".format(max))
    output.append("ping_min {}".format(min))
    output.append("ping_loss {}".format(loss))
    output.append('')
    return output

def trace(host, source):
    # Using source address?
    if source == '':
        trace_command = '{} {}'.format(filepath['traceroute'], host)
    else:
        trace_command = '{} -s {} {}'.format(filepath['traceroute'], source, host)

    #Log the actual ping command for debug purpose
    #Execute the ping
    cmd_output = subprocess.Popen(trace_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
    try:
        output = cmd_output[0].decode().split("\n")
    except IndexError:
        output = [trace_command, 'trace failed']

    return output

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

class GetHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        #Parse the url
        parsed_result = urlparse(self.path)
        value = parse_qs(parsed_result.query)
        # Retrieve the ping target
        address = value['target'][0]

        # Retrieve source address
        if "source" in value:
            source = value['source'][0]
        else:
            source = ''

        if "ping" in parsed_result.path:
            #Retrieve prot
            if "prot" in value:
                prot = value['prot'][0]
            else:
                prot = 4
            #Retrieve ping count
            if "count" in value:
                count = value['count'][0]
            else:
                count = 10
            #Retrieve ping packet size
            if "size" in value and int(value['size'][0]) < 10240:
                size = value['size'][0]
            else:
                size = 56
            #Retrieve ping interval
            if "interval" in value and int(value['interval'][0]) > 1:
                interval = value['interval'][0]
            else:
                interval = 500

            message = '\n'.join(ping(address, prot, interval, count, size, source))
        elif "trace" in parsed_result.path:
            message = '\n'.join(trace(address, source))
        else:
            pass

        #Prepare HTTP status code
        self.send_response(200)
        self.end_headers()
        self.wfile.write(message.encode())
        return

if __name__ == '__main__':
    #Locate the path of fping
    global filepath
    filepath = {}
    filepath['ping'] = locate("fping")
    filepath['traceroute'] = locate("traceroute")

    logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    #Check if there is a special port configured
    if len(sys.argv) >= 3:
        port = int(sys.argv[2])
    else:
        port = 8085
    logger.info('Starting server port {}, use <Ctrl-C> to stop'.format(port))
    server = ThreadedHTTPServer(('0.0.0.0', port), GetHandler)
    server.serve_forever()

from network_tests import *


def run_service_check(task, params):
    """Passes the params to the necessary service check and performs it"""
    if task == "Ping":
        return ping_service_check(*params)
    elif task == "Tracert":
        return tracert_service_check(*params)
    elif task == "HTTP":
        return http_service_check(*params)
    elif task == "HTTPS":
        return https_service_check(*params)
    elif task == "NTP":
        return ntp_service_check(*params)
    elif task == "DNS":
        return dns_service_check(*params)
    elif task == "TCP":
        return tcp_service_check(*params)
    elif task == "UDP":
        return udp_service_check(*params)
    elif task == "Echo":
        return echo_service_check(*params)


def ping_service_check(host, ttl, timeout, sequence_number):
    """Perform ping test and return results message"""
    msg = ""

    # Ping Test
    msg += "Ping Test:\n"
    ping_addr, ping_time = ping(host, ttl, timeout, sequence_number)
    if ping_addr and ping_time:
        msg += f"{host} (ping): {ping_addr[0]} - {ping_time:.2f} ms\n"
    else:
        msg += f"{host} (ping): Request timed out or no reply received\n"

    return msg


def tracert_service_check(host, max_hops, pings_per_hop, verbose):
    """Perform traceroute test and return results message"""
    msg = ""

    # Traceroute Test
    msg += "\nTraceroute Test:\n"
    msg += f"{host} (traceroute):\n"
    msg += traceroute(host, max_hops, pings_per_hop, verbose)

    return msg


def http_service_check(url):
    """Perform http test and return results message"""
    msg = ""

    # HTTP Request
    msg += f"Sending HTTP Request to {url} ... \n"
    http_server_status, http_server_response_code = check_server_http(url)
    msg += f"HTTP URL: {url}, HTTP server status: {http_server_status}, Status Code: {http_server_response_code if http_server_response_code is not None else 'N/A'}"

    return msg


def https_service_check(url, timeout):
    """Perform https test and return results message"""
    msg = ""

    # HTTP Request
    msg += f"Sending HTTPS Request to {url} ... \n"
    https_server_status, https_server_response_code, description = check_server_https(
        url, timeout
    )
    msg += f"HTTPS URL: {url}, HTTPS server status: {https_server_status}, Status Code: {https_server_response_code if https_server_response_code is not None else 'N/A'}, Description: {description}"

    return msg


def ntp_service_check(server):
    """Perform ntp test and return results message"""
    msg = ""

    # NTP Test
    msg += f"Testing Status of NTP Server {server} ... \n"
    ntp_server_status, ntp_server_time = check_ntp_server(server)
    msg += (
        f"{server} is up. Time: {ntp_server_time}"
        if ntp_server_status
        else f"{server} is down."
    )

    return msg


def dns_service_check(server, query, record_types):
    """Perform dns test and return results message"""
    msg = ""

    # DNS Test
    msg += f"Querying DNS Server {server} with Server {query} ... "
    for dns_record_type in record_types:
        dns_server_status, dns_query_results = check_dns_server_status(
            server, query, dns_record_type
        )
        msg += f"\nDNS Server: {server}, Status: {dns_server_status}, {dns_record_type} Records Results: {dns_query_results}"

    return msg


def tcp_service_check(ip_address, port):
    """Perform tcp test and return results message"""
    msg = ""

    # TCP test
    msg += f"Testing TCP to Server {ip_address} at Port {port} ... \n"
    tcp_port_status, tcp_port_description = check_tcp_port(ip_address, port)
    msg += f"Server: {ip_address}, TCP Port: {port}, TCP Port Status: {tcp_port_status}, Description: {tcp_port_description}"

    return msg


def udp_service_check(ip_address, port, timeout):
    """Perform udp test and return results message"""
    msg = ""

    # TCP test
    msg += f"Testing UDP to Server {ip_address} at Port {port} ... \n"
    udp_port_status, udp_port_description = check_udp_port(ip_address, port, timeout)
    msg += f"Server: {ip_address}, UDP Port: {port}, UDP Port Status: {udp_port_status}, Description: {udp_port_description}"

    return msg


def echo_service_check(ip_address, port):
    """Perform echo test and return results message"""
    msg = ""

    # TCP test
    msg += f"Testing TCP to Local Server {ip_address} at Port {port} ... \n"
    status, description = local_tcp_echo(ip_address, port)
    msg += f"Server: {ip_address}, TCP Port: {port}, TCP Port Status: {status}, Description: {description}"

    return msg

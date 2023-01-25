from prometheus_client import start_http_server, Counter, Info
import time
import asyncio
from sagemcom_api.enums import EncryptionMethod
from sagemcom_api.client import SagemcomClient
import asyncio
import os

HOST = os.environ['SAGEMCOM_HOST']
USERNAME = os.environ['SAGEMCOM_USERNAME']
PASSWORD = os.environ['SAGEMCOM_PASSWORD']
ENCRYPTION_METHOD = EncryptionMethod.SHA512
INTERVAL_SECONDS = int(os.environ['SAGEMCOM_POLL_INTERVAL_SECONDS'])


async def main() -> None:
    start_http_server(8000)


    async with SagemcomClient(HOST, USERNAME, PASSWORD, ENCRYPTION_METHOD) as client:
        try:
            await client.login()
        except Exception as exception:  # pylint: disable=broad-except
            print(f"failed to login! exception was: {exception}")
            exit(1)

        # Print device information of Sagemcom F@st router
        device_info = await client.get_device_info()
        info = Info('sagemcom_device_information', 'information about the sagencom device.')
        info.info({
            'mac_address': device_info.mac_address,
            'model_name': device_info.model_name,
            'model_number': device_info.model_number,
            'software_version': device_info.software_version,
            'hardware_version': device_info.hardware_version,
            'router_name': device_info.router_name,
            'gui_firmware_version': device_info.gui_firmware_version,
            'build_date': device_info.build_date,
        })


        sent_bytes = Counter('sagemcom_interface_sent_bytes', '', ['interface'])
        received_bytes = Counter('sagemcom_interface_received_bytes', '', ['interface'])
        sent_packets = Counter('sagemcom_interface_sent_packets', '', ['interface'])
        received_packets = Counter('sagemcom_interface_received_packets', '', ['interface'])
        # Print connected devices
        devices = await client.get_hosts()

        last_collected = time.monotonic()
        prior_data = await read_interfaces(client)
        while True:
            now = time.monotonic()
            sleep_time = max(0, last_collected + INTERVAL_SECONDS - now)
            await asyncio.sleep(sleep_time)
            last_collected += INTERVAL_SECONDS
            new_data = await read_interfaces(client)
            
            for interface in range(1,7): 
                prior_interface = prior_data[interface]
                new_interface = new_data[interface]

                sent_bytes.labels(interface=interface).inc(value_diff(prior_interface, new_interface, 'bytes_sent'))
                received_bytes.labels(interface=interface).inc(value_diff(prior_interface, new_interface, 'bytes_received'))
                sent_packets.labels(interface=interface).inc(value_diff(prior_interface, new_interface, 'packets_sent'))
                received_packets.labels(interface=interface).inc(value_diff(prior_interface, new_interface, 'packets_received'))
            prior_data = new_data


async def read_interfaces(client):
    data = {}
    for interface in range(1,7): 
        # print("interface {}".format(interface))
        custom_command_output = await client.get_value_by_xpath("Device/Ethernet/Interfaces/Interface[@uid='{}']/Stats".format(interface))
        stats = custom_command_output['stats']
        #print(custom_command_output)
        #print("sent {}b, recv {}b, sent {}pk, recv {}pk".format(
        #    custom_command_output['stats']['bytes_sent'],
        #    custom_command_output['stats']['bytes_received'],
        #    custom_command_output['stats']['packets_sent'],
        #    custom_command_output['stats']['packets_received'],
        #    ))
        data[interface] = {k:int(v) for (k,v) in custom_command_output['stats'].items()}
    return data

def value_diff(old_data, new_data, key):
    return new_data[key] - old_data[key]

asyncio.run(main())


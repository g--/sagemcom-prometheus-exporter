from prometheus_client import start_http_server, Counter, Info, Enum, Gauge
import time
import asyncio
from sagemcom_api.enums import EncryptionMethod
from sagemcom_api.client import SagemcomClient
import asyncio
import os
from aiohttp import ClientSession, ClientTimeout
from dataclasses import dataclass

HOST = os.environ['SAGEMCOM_HOST']
USERNAME = os.environ['SAGEMCOM_USERNAME']
PASSWORD = os.environ['SAGEMCOM_PASSWORD']
ENCRYPTION_METHOD = EncryptionMethod.SHA512
INTERVAL_SECONDS = int(os.environ['SAGEMCOM_POLL_INTERVAL_SECONDS'])

async def main() -> None:
    start_http_server(8000)

    interface_metrics = InterfaceMetrics(
        sent_bytes = Counter('sagemcom_interface_sent_bytes', '', ['interface']),
        received_bytes = Counter('sagemcom_interface_received_bytes', '', ['interface']),
        sent_packets = Counter('sagemcom_interface_sent_packets', '', ['interface']),
        received_packets = Counter('sagemcom_interface_received_packets', '', ['interface']),
        link_status = Enum('sagemcom_interface_status', '', ['interface'], states=['OK', 'UP', 'DOWN', 'DORMANT']),
        )


    async with SagemcomClient(HOST, USERNAME, PASSWORD, ENCRYPTION_METHOD) as client:
        try:
            await client.login()
            print("logged in")
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

        targets = [Interface(f"Device/Ethernet/Interfaces/Interface[@uid='{number}']") for number in range(1,7)]
        targets.append(OpticalInterface("Device/Optical/Interfaces/Interface[@uid='1']"))
        targets.append(SystemMetrics())
        targets.extend([WifiInterface(f"Device/WiFi/SSIDs/SSID[@uid='{number}']") for number in range(1,8)])
        for t in targets:
            await t.init(client)

        last_collected = time.monotonic()
        while True:
            now = time.monotonic()
            sleep_time = max(0, last_collected + INTERVAL_SECONDS - now)
            await asyncio.sleep(sleep_time)
            last_collected += INTERVAL_SECONDS

            for target in targets:
                await target.collect(client, interface_metrics)


class SystemMetrics:
    def __init__(self):
        self._total_memory = Gauge('sagemcom_system_total_memory', '', [])
        self._free_memory = Gauge('sagemcom_system_free_memory', '', [])

    async def init(self, client):
        pass

    async def collect(self, client, interface_metrics):
        results = await client.get_value_by_xpath("Device/DeviceInfo")
        self._total_memory.set(results["device_info"]["memory_status"]["total"])
        self._free_memory.set(results["device_info"]["memory_status"]["free"])


@dataclass
class InterfaceMetrics:
    sent_bytes: Counter
    received_bytes: Counter
    sent_packets: Counter
    received_packets: Counter
    link_status: Enum

class Interface:
    def __init__(self, xpath):
        self.xpath = xpath

    async def init(self, client):
        try:
            self.prior = self.convert_stat_results(await client.get_value_by_xpath(f"{self.xpath}/Stats"))
        except Exception:
            print(f"problem getting {self.xpath}")
            raise

    async def collect(self, client, interface_metrics):
        base_result = await client.get_value_by_xpath(self.xpath)
        stats_result = self.convert_stat_results(await client.get_value_by_xpath(f"{self.xpath}/Stats"))
        self.emit(base_result['interface'], stats_result, interface_metrics)
        self.prior = stats_result

    def emit(self, base, stats, interface_metrics):
        name = base['alias']

        #print("{} emitting {}b sent, {}b received, {}pk send, {}pk received".format(
        #    name,
        #    value_diff(self.prior, stats, 'bytes_sent'),
        #    value_diff(self.prior, stats, 'bytes_received'),
        #    value_diff(self.prior, stats, 'packets_sent'),
        #    value_diff(self.prior, stats, 'packets_received'),
        #    ))

        interface_metrics.sent_bytes.labels(interface=name).inc(value_diff(self.prior, stats, 'bytes_sent'))
        interface_metrics.received_bytes.labels(interface=name).inc(value_diff(self.prior, stats, 'bytes_received'))
        interface_metrics.sent_packets.labels(interface=name).inc(value_diff(self.prior, stats, 'packets_sent'))
        interface_metrics.received_packets.labels(interface=name).inc(value_diff(self.prior, stats, 'packets_received'))

        self.emit_link_state(base, interface_metrics)

    def convert_stat_results(self, results):
        stats = results['stats']
        return {k:int(v) for (k,v) in results['stats'].items()}

    def emit_link_state(self, base, interface_metrics):
        name = base['alias']
        interface_metrics.link_status.labels(interface=name).state(base['status'])

class OpticalInterface(Interface):
    pass

class WifiInterface(Interface):
    async def init(self, client):
        base_result = await client.get_value_by_xpath(self.xpath)
        self.prior = self.convert_stat_results(base_result['SSID'])

    async def collect(self, client, interface_metrics):
        base_result = await client.get_value_by_xpath(self.xpath)
        stats_result = self.convert_stat_results(base_result['SSID'])

        self.emit(base_result['SSID'], stats_result, interface_metrics)
        self.prior = stats_result


def value_diff(old_data, new_data, key):
    return new_data[key] - old_data[key]

asyncio.run(main())


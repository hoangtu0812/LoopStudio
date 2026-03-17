"""
Netstat Service - Logic lấy speedtest, thông số hệ thống, IP public.
Xử lý lỗi khi speedtest thất bại hoặc mất mạng.
"""
from dataclasses import dataclass

import psutil
import speedtest

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class NetstatResult:
    """Kết quả tổng hợp từ netstat."""

    download_mbps: float | None
    upload_mbps: float | None
    ping_ms: float | None
    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    public_ip: str | None
    speedtest_error: str | None = None


class NetstatService:
    """Service lấy thông tin mạng và hệ thống."""

    @staticmethod
    def _run_speedtest() -> tuple[float | None, float | None, float | None, str | None]:
        """
        Chạy speedtest-cli, trả về (download_mbps, upload_mbps, ping_ms, error).
        Trả về None nếu thất bại.
        """
        try:
            st = speedtest.Speedtest()
            st.get_best_server()
            download_bps = st.download()
            upload_bps = st.upload()
            ping_ms = st.results.ping

            download_mbps = round(download_bps / 1_000_000, 2)
            upload_mbps = round(upload_bps / 1_000_000, 2)
            return download_mbps, upload_mbps, ping_ms, None
        except Exception as e:
            logger.warning("Speedtest thất bại: %s", str(e))
            return None, None, None, str(e)

    @staticmethod
    def _get_public_ip() -> str | None:
        """Lấy địa chỉ IP public của server (dùng urllib - không cần curl)."""
        try:
            import urllib.request

            with urllib.request.urlopen("https://api.ipify.org", timeout=10) as resp:
                return resp.read().decode().strip()
        except Exception as e:
            logger.warning("Không lấy được IP public: %s", str(e))
            return None

    @classmethod
    def get_netstat(cls) -> NetstatResult:
        """Lấy toàn bộ thông tin netstat (speedtest + hệ thống + IP)."""
        download, upload, ping, speed_err = cls._run_speedtest()
        public_ip = cls._get_public_ip()

        # Thông tin CPU
        cpu_percent = psutil.cpu_percent(interval=1)

        # Thông tin RAM
        mem = psutil.virtual_memory()
        ram_percent = mem.percent
        ram_used_gb = round(mem.used / (1024**3), 2)
        ram_total_gb = round(mem.total / (1024**3), 2)

        # Thông tin Disk (partition gốc)
        disk = psutil.disk_usage("/")
        disk_percent = disk.percent
        disk_used_gb = round(disk.used / (1024**3), 2)
        disk_total_gb = round(disk.total / (1024**3), 2)

        return NetstatResult(
            download_mbps=download,
            upload_mbps=upload,
            ping_ms=ping,
            cpu_percent=cpu_percent,
            ram_percent=ram_percent,
            ram_used_gb=ram_used_gb,
            ram_total_gb=ram_total_gb,
            disk_percent=disk_percent,
            disk_used_gb=disk_used_gb,
            disk_total_gb=disk_total_gb,
            public_ip=public_ip,
            speedtest_error=speed_err,
        )

    @staticmethod
    def format_netstat_message(result: NetstatResult) -> str:
        """Format kết quả netstat thành message gửi Telegram."""
        lines = ["📊 **BÁO CÁO HỆ THỐNG**\n"]

        # Speedtest
        if result.speedtest_error:
            lines.append(f"🌐 **Speedtest:** ❌ Lỗi - {result.speedtest_error}")
        else:
            lines.append(
                f"🌐 **Speedtest:**\n"
                f"  • Download: {result.download_mbps} Mbps\n"
                f"  • Upload: {result.upload_mbps} Mbps\n"
                f"  • Ping: {result.ping_ms} ms"
            )

        # IP
        ip_str = result.public_ip or "Không xác định"
        lines.append(f"\n📍 **IP Public:** {ip_str}")

        # Tài nguyên
        lines.append(
            f"\n💻 **Tài nguyên Server:**\n"
            f"  • CPU: {result.cpu_percent}%\n"
            f"  • RAM: {result.ram_used_gb}/{result.ram_total_gb} GB ({result.ram_percent}%)\n"
            f"  • Disk: {result.disk_used_gb}/{result.disk_total_gb} GB ({result.disk_percent}%)"
        )

        return "\n".join(lines)

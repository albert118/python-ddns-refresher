import argparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os

from dotenv import load_dotenv

retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT"],
)

# Apply retries to session
adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("https://", adapter)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Refresh a Cloudflare DNS A record when your public IP changes."
    )
    parser.add_argument("--zone-id", required=True, help="Cloudflare zone ID.")
    parser.add_argument("--dns-record-id", required=True, help="Cloudflare DNS record ID.")
    parser.add_argument(
        "--dns-record-name",
        required=True,
        help="DNS record name (for example: home.example.com).",
    )
    parser.add_argument(
        "--last-ip-fn",
        default='last-known-ip.txt',
        help="Path to file that stores the last known IP address.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned DNS changes without sending a PUT request.",
    )
    return parser.parse_args()

def get_current_public_ip_address():
    url = 'https://api.ipify.org'
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.Timeout:
        print('❌ Timed out while fetching current public IP address')
        return None
    except requests.exceptions.RequestException as err:
        print(f'❌ Failed to fetch current public IP address: {err}')
        return None

def get_last_public_ip_address(fn):
    if os.path.exists(fn):
        with open(fn, 'r') as f:
            last_ip = f.read().strip()
            return last_ip
    else:
        print(f'Creating a new file to track the last known IP address: {fn}')
        with open(fn, 'w') as f: f.write('')
        return None

def save_ip_address(ip, fn):
    with open(fn, 'w') as f: f.write(ip)

def put_dns_update(zone_id, dns_record_id, dns_record_name, ip_address, api_token) -> dict:
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{dns_record_id}"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "type": "A",
        "name": dns_record_name,
        "content": ip_address,
        "ttl": 3600,
        "proxied": False,
    }

    try:
        response = session.put(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        # Cloudflare API result will include errors, messages, a success flag, and a result object
        data = response.json()
    except requests.exceptions.Timeout:
        print('❌ Timed out while updating Cloudflare DNS record')
        return {"success": False, "errors": [{"message": "request timeout"}]}
    except requests.exceptions.RequestException as err:
        print(f'❌ Failed to update Cloudflare DNS record: {err}')
        return {"success": False, "errors": [{"message": str(err)}]}

    if data.get("success"): return data

    if data.get("errors") and len(data["errors"]) > 0:
        print('⚠️ Errors were returned from Cloudflare.')
        for error in data["errors"]: print(error)

    return data

def init_env_variables(args):
    load_dotenv()

    cloudflare_api_token = os.getenv("CLOUDFLARE_API_TOKEN")
    if not cloudflare_api_token:
        raise ValueError("CLOUDFLARE_API_TOKEN is not set")

    dns_record_name = args.dns_record_name
    cloudflare_zone_id = args.zone_id
    cloudflare_dns_record_id = args.dns_record_id
    last_ip_fn = args.last_ip_fn

    return {
        "CLOUDFLARE_API_TOKEN": cloudflare_api_token,
        "DNS_RECORD_NAME": dns_record_name,
        "CLOUDFLARE_ZONE_ID": cloudflare_zone_id,
        "CLOUDFLARE_DNS_RECORD_ID": cloudflare_dns_record_id,
        "LAST_IP_FN": last_ip_fn,
    }

if __name__ == "__main__":
    args = parse_args()
    env = init_env_variables(args)
    curr_ip = get_current_public_ip_address()
    if not curr_ip:
        raise SystemExit(1)

    last_ip = get_last_public_ip_address(fn=env["LAST_IP_FN"])

    if last_ip == curr_ip:
        print('✅ Last known IP is the same, exiting now')
    else:
        print(f'🆕 New address found. Updating Cloudflare record with: {curr_ip}')
        if args.dry_run:
            print('🧪 Dry-run mode enabled. No request was sent to Cloudflare.')
            print(
                f"Would update zone '{env['CLOUDFLARE_ZONE_ID']}', "
                f"record '{env['CLOUDFLARE_DNS_RECORD_ID']}' "
                f"({env['DNS_RECORD_NAME']}) to IP '{curr_ip}'."
            )
            raise SystemExit(0)

        result = put_dns_update(
            zone_id=env["CLOUDFLARE_ZONE_ID"],
            dns_record_id=env["CLOUDFLARE_DNS_RECORD_ID"],
            dns_record_name=env["DNS_RECORD_NAME"],
            ip_address=curr_ip,
            api_token=env["CLOUDFLARE_API_TOKEN"],
        )
        print(f"☁️ Cloudflare response success: {result.get('success')}")
        # persist the last known address only if we can update the DNS record
        if result.get("success"):
            save_ip_address(curr_ip, fn=env["LAST_IP_FN"])
            print(f'📃 DNS record updated. Persisted last known IP to file: {env["LAST_IP_FN"]}')

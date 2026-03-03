# Python DDNS Refresher

A script to help check and update public IP addresses. If it's found, it pushes the
updated address to Cloudflare using their API.

This service uses <https://api.ipify.org> to resolve the current network's public facing IP address. This is quite a nice service, as it is free and allows millions of RPS without issue. See their docs [here](https://www.ipify.org/) for more.

## Requirements

- Python 3.9+
- A Cloudflare API token with DNS edit permissions for your zone

## Setup

1. Install dependencies:

```sh
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and set your token:

```dotenv
CLOUDFLARE_API_TOKEN=your_token_here
```

## Usage

Run the script with required CLI arguments:

```sh
python main.py \
	--zone-id <cloudflare_zone_id> \
	--dns-record-id <cloudflare_dns_record_id> \
	--dns-record-name <record_name> \
	--last-ip-fn <path_to_ip_cache_file>
```

### Required arguments

- `--zone-id`: Cloudflare zone ID
- `--dns-record-id`: Cloudflare DNS record ID
- `--dns-record-name`: DNS A record name (example: `home.example.com`)

### Optional arguments

- `--last-ip-fn`: File used to store the previously known public IP (defaults to `last-known-ip.txt`)
- `--dry-run`: Print what would change without sending a Cloudflare update request

### Dry run example

```bash
python main.py \
	--zone-id <cloudflare_zone_id> \
	--dns-record-id <cloudflare_dns_record_id> \
	--dns-record-name <record_name> \
	--dry-run
```

## Scheduling

Run this script on an interval (for example every 5 minutes) using your scheduler of choice:

- Linux/macOS: `cron`
- Windows: Task Scheduler

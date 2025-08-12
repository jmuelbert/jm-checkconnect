# Installation

## Prerequisites

- Python 3.6 or later
- pip 19.0 or later

## Installation Steps

- Clone the repository: git clone https://github.com/jmuelbert/checkconnect.git
- Change into the directory: cd checkconnect
- Install the dependencies: `bash pip install -r requirements.txt`
- Run the program: python checkconnect.py

## Configuration

### Config File

The config file is located at config.json. You can edit this file to add or remove websites and NTP servers.
Config Options

- websites: a list of websites to check
- ntp_servers: a list of NTP servers to check
- timeout: the timeout value for the checks (in seconds)

## Example Config File

```json
{
  "websites": ["https://www.example.com", "https://www.google.com"],
  "ntp_servers": ["time.nist.gov", "time.apple.com"],
  "timeout": 5
}
```

### Description pyproject.toml

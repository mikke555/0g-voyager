##  🚀 Installation
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## ⚙️ Settings

```env
#######################################################################
#                        General Settings                             #
#######################################################################

SHUFFLE_WALLETS = True
USE_PROXY = True

SLEEP_BETWEEN_WALLETS = [10, 20]
SLEEP_BETWEEN_ACTIONS = [5, 10]
RETRY_COUNT = 1

MAX_GWEI = 30

#######################################################################
#                        Intract Settings                             #
#######################################################################

ALLOW_MULTIPLE_MINTS = False
USE_REF = False
REF_CODE = ""

#######################################################################
#                        Send A0GI Settings                           #
#######################################################################

SEND_VALUE_PERCENTAGE = [5, 10]
```
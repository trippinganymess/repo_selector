import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_BASE_URL = "https://api.github.com"

DEFAULT_LIMIT = 100
DEFAULT_EXPORT_CSV = False
MIN_STARS = 500
MAX_STARS = 50000
MIN_PY_FILES = 15
MAX_PY_FILES = 100
MAX_REPO_SIZE_KB = 100000
MAX_TOTAL_FILES = 500
CACHE_TTL_HOURS = 24
MAX_CONCURRENT_REQUESTS = 10
REQUEST_TIMEOUT = 30

ALLOWED_LICENSES = {
    "MIT",
    "Apache-1.0",
    "Apache-1.1", 
    "Apache-2.0",
    "Apache-2.0-Modified",
    "Apache-with-LLVM-Exception",
    "Apache-with-Runtime-Exception",
    "BSD-1-Clause",
    "BSD-2-Clause",
    "BSD-2-Clause-Flex",
    "BSD-2-Clause-FreeBSD",
    "BSD-2-Clause-Modification",
    "BSD-2-Clause-Patent",
    "BSD-2-Clause-Views",
    "BSD-3-Clause",
    "BSD-3-Clause-Attribution",
    "BLAS",
    "BSD-3-Clause-EricHeitz",
    "BSD-3-Clause-HealthLevelSeven",
    "BSD-3-Clause-LBNL",
    "BSD-3-Clause-Modification",
    "BSD-3-Clause-OpenMPI",
    "BSD-3-Clause-plus-CMU-Attribution",
    "BSD-3-Clause-plus-Paul-Mackerras-Attribution",
    "BSD-3-Clause-plus-Tommi-Komulainen-Attribution",
    "BSD-4-Clause",
    "BSD-4-Clause-Argonne",
    "BSD-4-Clause-Atmel",
    "BSD-4-Clause-Giffin",
    "BSD-4-Clause-PC-SC-Lite",
    "BSD-4-Clause-Plus-Modification-Notice",
    "BSD-4-Clause-UC",
    "BSD-4-Clause-Visigoth",
    "BSD-4-Clause-Vocal",
    "BSD-4-Clause-Wasabi",
    "BSD-4.3TAHOE",
    "BSD-5-Clause",
    "BSD-FatFs",
    "BSD-Mixed-2-Clause-And-3-Clause",
    "BSD-Protection",
    "BSD-Source-Code",
    "BSL-1.0",
    "CC-BY-1.0",
    "CC-BY-2.0",
    "CC-BY-2.5",
    "CC-BY-3.0",
    "CC-BY-4.0",
    "GNU-All-permissive-Copying-License",
    "GPL-2.0-with-autoconf-exception",
    "GPL-2.0-with-classpath-exception",
    "GPL-3.0-with-autoconf-exception"
}

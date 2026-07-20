import sys
sys.path.insert(0, ".")

from server.main import app
from mangum import Mangum

handler = Mangum(app)

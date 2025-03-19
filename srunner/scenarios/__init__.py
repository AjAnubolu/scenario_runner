from __future__ import print_function

# Import what we need for our scenario
import sys
import os

# Make sure the system knows about the srunner package
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Now use absolute imports
from srunner.scenarios.low_visibility_night import LowVisibilityNightDriving

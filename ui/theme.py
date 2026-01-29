"""
Bloomberg Terminal theme constants.

Defines color scheme and typography for the trading dashboard UI.
Strictly enforces institutional trading platform aesthetic with monochrome
colors, terminal green/red accents, and monospace fonts.
"""

# Color Palette - Bloomberg Terminal Style
BG_BLACK = "#000000"           # Main background
BG_DARK_GREY = "#121212"       # Card backgrounds, secondary surfaces
TERMINAL_GREEN = "#00FF00"     # Profit, positive values, buy signals
SIGNAL_RED = "#FF0000"         # Loss, negative values, sell signals
TEXT_WHITE = "#FFFFFF"         # Primary text
TEXT_GREY = "#CCCCCC"          # Secondary text, labels
BORDER_GREY = "#333333"        # Borders, dividers, separators

# Typography - Monospace Only
FONT_MONO = "Consolas, 'Courier New', Monaco, monospace"
FONT_SIZE_LARGE = "48px"       # Metric values (emphasis)
FONT_SIZE_MEDIUM = "24px"      # Section headers
FONT_SIZE_NORMAL = "16px"      # Body text, labels
FONT_SIZE_SMALL = "14px"       # Footnotes, captions

# Layout Constants
BORDER_RADIUS = "0px"          # No rounded corners (sharp edges only)
BORDER_WIDTH = "1px"
PADDING_SMALL = "8px"
PADDING_MEDIUM = "16px"
PADDING_LARGE = "24px"

# Chart Colors
CHART_CANDLESTICK_UP = TERMINAL_GREEN
CHART_CANDLESTICK_DOWN = SIGNAL_RED
CHART_BB_COLOR = TEXT_GREY
CHART_RSI_COLOR = TEXT_WHITE
CHART_GRID_COLOR = "#1a1a1a"

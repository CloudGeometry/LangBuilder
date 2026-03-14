"""
Savings Calculator - LangBuilder Custom Component

Calculates projected cloud savings based on annual spend,
with formatted currency output for PDF reports.

Author: CloudGeometry
Project: Carter's Agents - Content Engine
"""

from lfx.custom import Component
from lfx.inputs.inputs import HandleInput
from lfx.io import FloatInput, Output
from lfx.schema import Data


class SavingsCalculator(Component):
    """
    Calculates projected cloud savings based on annual spend.

    This component is used by the Content Engine agent to generate
    personalized savings projections for PDF reports. It applies
    CloudGeometry's standard optimization rate to calculate potential savings.
    """

    display_name = "Savings Calculator"
    description = "Calculates projected cloud savings based on annual spend"
    icon = "dollar-sign"
    name = "SavingsCalculator"

    # Default savings rate (30% is industry standard for cloud optimization)
    DEFAULT_SAVINGS_RATE = 0.30

    # Fallback message when no spend data provided
    NO_DATA_MESSAGE = "Contact us for a custom estimate"

    inputs = [
        HandleInput(
            name="annual_cloud_spend",
            display_name="Annual Cloud Spend",
            required=False,
            input_types=["Message", "Data"],
            info="Annual cloud infrastructure spend in USD (e.g., 500000 for $500,000). Accepts numeric string or Data object."
        ),
        FloatInput(
            name="savings_rate",
            display_name="Savings Rate",
            required=False,
            value=0.30,
            info="Projected savings rate as decimal (default: 0.30 = 30%)",
            advanced=True
        ),
    ]

    outputs = [
        Output(
            name="savings",
            display_name="Calculated Savings",
            method="calculate_savings",
        ),
    ]

    def _format_currency(self, amount: int) -> str:
        """Format an integer as US currency with commas."""
        if amount is None or amount == 0:
            return "N/A"
        return f"${amount:,}"

    def _extract_int(self, value, key: str = "annual_cloud_spend") -> int:
        """Extract integer from a Message, Data object, or string."""
        if value is None:
            return 0
        # Handle Message objects
        if hasattr(value, 'text'):
            text = str(value.text).strip()
        # Handle Data objects (have .data attribute with dict)
        elif hasattr(value, 'data') and isinstance(value.data, dict):
            if key in value.data:
                text = str(value.data[key]).strip()
            else:
                # Try to find a numeric value
                for v in value.data.values():
                    try:
                        text = str(v).replace('$', '').replace(',', '').strip()
                        return int(float(text))
                    except (ValueError, TypeError):
                        continue
                return 0
        # Handle dict
        elif isinstance(value, dict):
            if key in value:
                text = str(value[key]).strip()
            else:
                return 0
        else:
            text = str(value).strip()
        # Remove currency symbols, commas, and parse
        text = text.replace('$', '').replace(',', '').strip()
        try:
            return int(float(text))  # Handle "500000.0" format
        except (ValueError, TypeError):
            return 0

    def calculate_savings(self) -> Data:
        """
        Calculate projected savings based on annual cloud spend.

        Returns:
            Data object with formatted savings and raw values
        """
        # Get savings rate (use default if not provided)
        rate = self.savings_rate if self.savings_rate is not None else self.DEFAULT_SAVINGS_RATE

        # Extract integer from Message or string input
        annual_spend = self._extract_int(self.annual_cloud_spend)

        # Check if we have valid spend data
        if annual_spend == 0:
            self.status = "⚠️ No spend data - using fallback"
            return Data(data={
                "calculated_savings": self.NO_DATA_MESSAGE,
                "savings_amount": 0,
                "annual_spend_formatted": "N/A",
                "annual_spend_raw": 0,
                "savings_rate": rate,
                "has_spend_data": False
            })

        # Calculate savings
        savings_amount = int(annual_spend * rate)

        # Format for display
        savings_formatted = self._format_currency(savings_amount)
        spend_formatted = self._format_currency(annual_spend)

        self.status = f"✅ Projected savings: {savings_formatted}"

        return Data(data={
            "calculated_savings": savings_formatted,
            "savings_amount": savings_amount,
            "annual_spend_formatted": spend_formatted,
            "annual_spend_raw": annual_spend,
            "savings_rate": rate,
            "has_spend_data": True
        })

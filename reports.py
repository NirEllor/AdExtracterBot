reports = {
    "Ford_2024_yearly_1711271.xlsx",
    "Nissan_2024_yearly_1711275.xlsx",
    "Jamba_Juice_Yearly_2024_1727847.xlsx",
    "7_eleven_Yearly_2024_1727830.xlsx",
    "Heinz_Yearly_2024_1727840.xlsx",
    "Nestle_Yearly_2024_1727843.xlsx",
    "Oreos_Yearly_2024_1727835.xlsx",
    "Pizza_Hut_Yearly_2024_1727834.xlsx",
    "Starbucks_Yearly_2024_1727850.xlsx",
    "Wendys_Yearly_2024_1727844.xlsx",
    "Arbys_Yearly_2024_1727828.xlsx",
    "Breyers_Ice_Cream_Yearly_2024_1727806.xlsx",
    "Dominos_Pizza_Yearly_2024_1727803.xlsx",
    "Activia_2024_Yearly_1727780.xlsx",
    "Cheerios_Yearly_2024_1727802.xlsx",
    "Dunkin_Donuts_2024_Yearly_2024_1727795.xlsx",
    "Kraft_2024_Yearly_2024_1727790.xlsx",
    "Papa_Johns_2024_Yearly_1727776.xlsx",
    "Whole_Foods_2024_Yearly_1727778.xlsx",
    "Hershey_2024_Yearly_1727773.xlsx",
    "Taco_Bell_2024_Yearly_1727769.xlsx",
    "Subway_Yearly_2024_1727810.xlsx",
    "Dairy_Queen_Yearly_2024_1727817.xlsx",
    "Burger_King_2024_Yearly_1727765.xlsx",
    "Mazda_2024_Yearly_1711274.xlsx",
    "Frito_Lay_2024_Yearly_1727770.xlsx",
    "Five_Guys_Yearly_2024_1727822.xlsx",
    "Outback_Steakhouse_2024_Yearly_1727772.xlsx"
}

def to_failed_filename(s: str) -> str:
    prefix = s.split("_", 1)[0]
    return prefix + "_failed_to_download.xlsx"


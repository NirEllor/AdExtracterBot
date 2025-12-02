brands = {"activia"

}


def to_failed_filename(s: str) -> str:
    prefix = s.split("_", 1)[0]
    return prefix + "_failed_to_download.xlsx"


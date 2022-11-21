

def lbl_keyword(lbl_filename, keyword):
    """Output a keyword value from a lbl file
    
    ARGUMENTS
    ---------   
    lbl_filename: string
        lbl filename
    keyword: string
        keyword to read
    
    RETURN
    ------
    float
    """
    with open (lbl_filename, "r") as myfile:
        lines = myfile.readlines()

    for line in lines:
        if keyword in line:
            value = "".join(line.split()).split('=')[-1].replace('"', '')
    
    # Set correct output type
    try:
        if '.' in value:
            return float(value)
        else:
            return int(value)
    except  ValueError:
        return value

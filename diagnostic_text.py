def print_warning(message):
    '''
    Print a yellow warning label before message.
    :param message: the warning message.
    :return: None
    '''
    print("\033[40;33mWARNING\033[0m: " + str(message) + ".")


def print_error(message):
    '''
    Print a red error label before message.
    :param message: the error message.
    :return: None
    '''
    print("\033[1;31mERROR\033[0m: " + str(message) + ".")

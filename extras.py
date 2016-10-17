import re
import random


def roll_dice_cmd(cmd):
    def roll_dice(dice, sides, plus=0):
        message = ""
        for i in range(0, dice):
            message += "%d " % (random.randrange(0 + 1, sides + 1) + plus)
        return message

    args = cmd[1:].split("d")

    dice = None
    sides = None
    plus = 0

    if args[0] == '':
        args[0] = '1'

    try:
        dice = int(args[0])
        if (args[1].find("+") != -1):
            sides, plus = args[1].split("+")
            sides = int(sides)
            plus = int(plus)
        else:
            sides = int(args[1])
    except ValueError:
        return "Syntax Error!"

    return roll_dice(dice, sides, plus)


def command_router(cmd):
    if re.match("!\d{0,1}d\d{0,10}", cmd):
        return roll_dice_cmd(cmd)
    elif re.match("!d\d{0,10}", cmd):
        return roll_dice_cmd(cmd)
    return "No such command!"

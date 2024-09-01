import json
import discord

"""
Integration for Enchant Order
Note: Code below is not mine! Large majority of it is copied from https://github.com/iamcal/enchant-order/blob/main/work.js and translated to Python. I only integrated it into my bot.
"""


def process(item_namespace, enchantment_foundation, mode="levels"):
    enchanted_item_objs = generateEnchantedItems(item_namespace, enchantment_foundation)
    cheapest_work2item = cheapestItemsFromList(enchanted_item_objs)
    cheapest_item_obj = None
    if mode == "levels":
        cheapest_item_obj = cheapestItemFromDictionaryByLevels(cheapest_work2item)
    elif mode == "prior_work":
        cheapest_item_obj = cheapestItemFromDictionaryByPriorWork(cheapest_work2item)
    instructions = []
    try:
        instructions = cheapest_item_obj.getInstructions()
    except TypeError:
        pass
    return {
        "msg": "complete",
        "item_obj": cheapest_item_obj,
        "instructions": instructions
    }


def combinations(set, k):
    if k > len(set) or k <= 0:
        return []
    if k == len(set):
        return [set]
    if k == 1:
        combs = []
        for i in range(len(set)):
            combs.append([set[i]])
        return combs
    combs = []
    for i in range(len(set) - k + 1):
        head = set[i:i + 1]
        tailcombs = combinations(set[i + 1:], k - 1)
        for j in range(len(tailcombs)):
            combs.append(head + tailcombs[j])
    return combs


def isInt(obj):
    return obj % 1 == 0


def isNaturalNumber(obj):
    is_int = isInt(obj)
    is_positive = obj >= 0
    return is_int and is_positive


def isPositiveInt(obj):
    is_int = isInt(obj)
    is_positive = obj > 0
    return is_int and is_positive


def hashFromItem(item_obj):
    enchantments_obj = item_obj.enchantments_obj
    enchantment_objs = enchantments_obj.enchantment_objs
    enchantment_objs_length = len(enchantment_objs)
    enchantment_ids = [0] * enchantment_objs_length
    enchantment_levels = [0] * enchantment_objs_length
    for enchantment_index, enchantment_obj in enumerate(enchantment_objs):
        enchantment_ids[enchantment_index] = enchantment_obj.id
        enchantment_levels[enchantment_index] = enchantment_obj.level
    sorted_ids = sorted(enchantment_ids)
    sorted_levels = [0] * enchantment_objs_length
    for id_index, id in enumerate(sorted_ids):
        sorted_levels[id_index] = enchantment_ids[enchantment_ids.index(id)]
    item_namespace = item_obj.item_namespace
    prior_work = item_obj.prior_work
    item_hash = (item_namespace, tuple(sorted_ids), tuple(sorted_levels), prior_work)
    return item_hash


def memoizeHashFromArguments(arguments):
    enchanted_item_objs = arguments[0]
    enchanted_item_hashes = []
    for enchanted_item_index, enchanted_item_obj in enumerate(enchanted_item_objs):
        item_hash = hashFromItem(enchanted_item_obj)
        enchanted_item_hashes.append(item_hash)
    return tuple(enchanted_item_hashes)


def memoizeCheapest(func):
    results = {}

    def wrapper(*arguments):
        args_key = memoizeHashFromArguments(arguments)
        if args_key not in results:
            results[args_key] = func(*arguments)
        return results[args_key]
    return wrapper


def compareCheapest(item_obj1, item_obj2):
    work2item = {}
    try:
        prior_work1 = item_obj1.prior_work
    except TypeError:
        prior_work2 = item_obj2.prior_work
        work2item[prior_work2] = item_obj2
        return work2item
    try:
        prior_work2 = item_obj2.prior_work
    except TypeError:
        prior_work1 = item_obj1.prior_work
        work2item[prior_work1] = item_obj1
        return work2item
    if prior_work1 == prior_work2:
        cumulative_levels1 = item_obj1.cumulative_levels
        cumulative_levels2 = item_obj2.cumulative_levels
        if cumulative_levels1 == cumulative_levels2:
            cumulative_minimum_xp1 = item_obj1.cumulative_minimum_xp
            cumulative_minimum_xp2 = item_obj2.cumulative_minimum_xp
            if cumulative_minimum_xp1 <= cumulative_minimum_xp2:
                work2item[prior_work1] = item_obj1
            else:
                work2item[prior_work2] = item_obj2
        elif cumulative_levels1 < cumulative_levels2:
            work2item[prior_work1] = item_obj1
        else:
            work2item[prior_work2] = item_obj2
    else:
        work2item[prior_work1] = item_obj1
        work2item[prior_work2] = item_obj2
    return work2item


def cheapestItemFromDictionaryByPriorWork(work2item):
    prior_works = list(work2item.keys())
    cheapest_prior_work = prior_works[0]
    cheapest_item_obj = work2item[cheapest_prior_work]
    return cheapest_item_obj


def cheapestItemFromDictionaryByLevels(work2item):
    prior_works = list(work2item.keys())
    cheapest_count = len(prior_works)
    potential_costs = [0] * cheapest_count
    cheapest_levels = None
    cheapest_index = None
    for index, prior_work in enumerate(prior_works):
        item_obj = work2item[prior_work]
        cumulative_levels = item_obj.cumulative_levels
        potential_costs[index] = cumulative_levels
        if cheapest_levels is None or cumulative_levels < cheapest_levels:
            cheapest_levels = cumulative_levels
            cheapest_index = index
    cheapest_prior_work = prior_works[cheapest_index]
    cheapest_item_obj = work2item[cheapest_prior_work]
    return cheapest_item_obj


def cheapestItemFromItems2(left_item_obj, right_item_obj):
    try:
        normal_item_obj = combineEnchantedItem(left_item_obj, right_item_obj)
    except (MergeLevelsTooExpensiveError, BookNotOnRightError):
        return combineEnchantedItem(right_item_obj, left_item_obj)
    try:
        reversed_item_obj = combineEnchantedItem(right_item_obj, left_item_obj)
    except (MergeLevelsTooExpensiveError, BookNotOnRightError):
        return normal_item_obj
    cheapest_work2item = compareCheapest(normal_item_obj, reversed_item_obj)
    prior_works = list(cheapest_work2item.keys())
    prior_work = prior_works[0]
    cheapest_item_obj = cheapest_work2item[prior_work]
    return cheapest_item_obj


def removeExpensiveCandidatesFromDictionary(work2item):
    cheapest_work2item = {}
    cheapest_levels = None
    for prior_work, item_obj in work2item.items():
        cumulative_levels = item_obj.cumulative_levels
        if cheapest_levels is None or (cumulative_levels < cheapest_levels):
            cheapest_work2item[prior_work] = item_obj
            cheapest_levels = cumulative_levels
    return cheapest_work2item


def cheapestItemsFromDictionaries2(left_work2item, right_work2item):
    cheapest_work2item = {}
    cheapest_prior_works = []
    for left_prior_work, left_item_obj in left_work2item.items():
        for right_prior_work, right_item_obj in right_work2item.items():
            try:
                new_work2item = cheapestItemsFromList([left_item_obj, right_item_obj])
            except (MergeLevelsTooExpensiveError, BookNotOnRightError):
                pass
            else:
                for new_prior_work, new_item_obj in new_work2item.items():
                    prior_work_exists = new_prior_work in cheapest_prior_works
                    if prior_work_exists:
                        cheapest_item_obj = cheapest_work2item[new_prior_work]
                        new_cheapest_work2item = compareCheapest(cheapest_item_obj, new_item_obj)
                        new_cheapest_item_obj = new_cheapest_work2item[new_prior_work]
                        cheapest_work2item[new_prior_work] = new_cheapest_item_obj
                    else:
                        cheapest_work2item[new_prior_work] = new_item_obj
                        cheapest_prior_works.append(new_prior_work)
    cheapest_work2item = removeExpensiveCandidatesFromDictionary(cheapest_work2item)
    return cheapest_work2item


def cheapestItemsFromListN(item_objs):
    item_count = len(item_objs)
    max_item_subcount = item_count // 2
    cheapest_work2item = {}
    cheapest_prior_works = []
    for item_subcount in range(1, max_item_subcount + 1):
        for left_item_objs in combinations(item_objs, item_subcount):
            right_item_objs = [item_obj for item_obj in item_objs if item_obj not in left_item_objs]
            left_work2item = cheapestItemsFromList(left_item_objs)
            right_work2item = cheapestItemsFromList(right_item_objs)
            new_work2item = cheapestItemsFromDictionaries([left_work2item, right_work2item])
            for new_prior_work, new_item_obj in new_work2item.items():
                prior_work_exists = new_prior_work in cheapest_prior_works
                if prior_work_exists:
                    cheapest_item_obj = cheapest_work2item[new_prior_work]
                    new_cheapest_work2item = compareCheapest(cheapest_item_obj, new_item_obj)
                    new_cheapest_item_obj = new_cheapest_work2item[new_prior_work]
                    cheapest_work2item[new_prior_work] = new_cheapest_item_obj
                else:
                    cheapest_work2item[new_prior_work] = new_item_obj
                    cheapest_prior_works.append(new_prior_work)
    return cheapest_work2item


@memoizeCheapest
def cheapestItemsFromList(item_objs):
    item_count = len(item_objs)
    if item_count == 1:
        item_obj = item_objs[0]
        prior_work = item_obj.prior_work
        work2item = {prior_work: item_obj}
        return work2item
    elif item_count == 2:
        left_item_obj, right_item_obj = item_objs
        cheapest_item_obj = cheapestItemFromItems2(left_item_obj, right_item_obj)
        cheapest_prior_work = cheapest_item_obj.prior_work
        work2item = {cheapest_prior_work: cheapest_item_obj}
        return work2item
    else:
        work2item = cheapestItemsFromListN(item_objs)
        return work2item


def cheapestItemsFromDictionaries(work2items):
    work2item_count = len(work2items)
    if work2item_count == 1:
        return work2items[0]
    elif work2item_count == 2:
        left_work2item, right_work2item = work2items
        return cheapestItemsFromDictionaries2(left_work2item, right_work2item)


def combineEnchantment(left_enchantment_obj, right_enchantment_obj):
    left_enchantment_id = left_enchantment_obj.id
    right_enchantment_id = right_enchantment_obj.id
    if left_enchantment_id == right_enchantment_id:
        left_level = left_enchantment_obj.level
        right_level = right_enchantment_obj.level
        if left_level == right_level:
            new_level = left_level + 1
        else:
            new_level = max(left_level, right_level)
        new_enchantment = Enchantment(left_enchantment_id, new_level)
        merge_levels = new_enchantment.levels
        return Enchantments([new_enchantment], merge_levels)
    else:
        merge_levels = right_enchantment_obj.levels
        return Enchantments([left_enchantment_obj, right_enchantment_obj], merge_levels)


class Enchantment:
    def __init__(self, enchantment_id, level):
        self.id = enchantment_id
        if enchantment_id not in ENCHANTMENT2WEIGHT:
            print(ENCHANTMENT2WEIGHT)
            print(enchantment_id)
            raise ValueError("invalid enchantment name")
        if not isPositiveInt(level):
            raise ValueError("level must be positive integer")
        self.level = int(level)
        weight = int(ENCHANTMENT2WEIGHT[enchantment_id])
        self.levels = int(level) * int(weight)
        self.namespace = self.getNamespace()

    def getNamespace(self):
        enchantment_id = self.id
        enchantment_namespaces = list(ENCHANTMENT2ID.keys())
        enchantment_namespace = next(key for key, value in ENCHANTMENT2ID.items() if value == enchantment_id)
        return enchantment_namespace


def combineEnchantments(left_enchantments_obj, right_enchantments_obj):
    merge_levels = 0
    merged_enchantment_objs = []
    left_enchantment_objs = left_enchantments_obj.enchantment_objs
    left_enchantment_ids = [enchantment_obj.id for enchantment_obj in left_enchantment_objs]
    left_enchantment_ids = tuple(left_enchantment_ids)
    right_enchantment_objs = right_enchantments_obj.enchantment_objs
    common_left_enchantments = []
    for right_enchantment_obj in right_enchantment_objs:
        right_enchantment_id = right_enchantment_obj.id
        if right_enchantment_id in left_enchantment_ids:
            left_enchantment_index = left_enchantment_ids.index(right_enchantment_id)
            left_enchantment_obj = left_enchantment_objs[left_enchantment_index]
            common_left_enchantments.append(left_enchantment_obj)
            merged_enchantments_obj = combineEnchantment(left_enchantment_obj, right_enchantment_obj)
            merge_levels += merged_enchantments_obj.merge_levels
            merged_enchantment_objs.extend(merged_enchantments_obj.enchantment_objs)
        else:
            merge_levels += right_enchantment_obj.levels
            merged_enchantment_objs.append(right_enchantment_obj)
    for enchantment_obj in left_enchantment_objs:
        if enchantment_obj not in common_left_enchantments:
            merged_enchantment_objs.append(enchantment_obj)
    return Enchantments(merged_enchantment_objs, merge_levels)


class Enchantments:
    def __init__(self, enchantment_objs, merge_levels=0):
        for enchantment_obj in enchantment_objs:
            if not isinstance(enchantment_obj, Enchantment):
                raise TypeError("each enchantment must be of type Enchantment")
        self.enchantment_objs = enchantment_objs
        self.merge_levels = merge_levels
        levels = 0
        for enchantment_obj in enchantment_objs:
            levels += int(enchantment_obj.levels)
        self.levels = levels


def combineEnchantedItem(left_item_obj, right_item_obj):
    return MergedEnchantedItem(left_item_obj, right_item_obj)


def experienceFromLevel(level):
    if level == 0:
        return 0
    elif level <= 16:
        return level * level + 7
    elif level <= 31:
        return 2.5 * level * level - 40.5 * level + 360
    else:
        return 4.5 * level * level - 162.5 * level + 2220


def priorWork2Penalty(prior_work):
    return 2 ** prior_work - 1


class InvalidEnchantmentError(Exception):
    def __init__(self, message="enchantment incompatible for item namespace"):
        super().__init__(message)
        self.name = "IncompatibleEnchantmentError"


class InvalidItemNameError(Exception):
    def __init__(self, message="invalid item name"):
        super().__init__(message)
        self.name = "InvalidItemNameError"


class EnchantedItem:
    def __init__(self, item_namespace, enchantments_obj, prior_work=0, cumulative_levels=0, cumulative_minimum_xp=0):
        if item_namespace not in ITEM_NAMESPACES:
            raise InvalidItemNameError("invalid item namespace")
        if item_namespace != "book":
            valid_enchantments = ITEM2ENCHANTMENTS[item_namespace]
            enchantment_objs = enchantments_obj.enchantment_objs
            for enchantment_obj in enchantment_objs:
                enchantment_id = enchantment_obj.id
                if enchantment_id not in valid_enchantments:
                    raise InvalidEnchantmentError("invalid or incompatible enchantment for item namespace")
        if not isNaturalNumber(prior_work):
            raise ValueError("prior work must be non-negative integer")
        if not isNaturalNumber(cumulative_levels):
            raise ValueError("cumulative levels must be non-negative integer")
        self.item_namespace = item_namespace
        self.enchantments_obj = enchantments_obj
        self.prior_work = prior_work
        self.cumulative_levels = cumulative_levels
        self.cumulative_minimum_xp = cumulative_minimum_xp
        self.maximum_xp = experienceFromLevel(cumulative_levels)


class IncompatibleItemsError(Exception):
    def __init__(self, message="(1) at least one item must be book or (2) both items must be same"):
        super().__init__(message)
        self.name = "IncompatibleItemsError"


class BookNotOnRightError(Exception):
    def __init__(self, message="book must be on right if other item is not book"):
        super().__init__(message)
        self.name = "BookNotOnRightError"


class MergeLevelsTooExpensiveError(Exception):
    def __init__(self, message="merge levels is above maximum allowed"):
        super().__init__(message)
        self.name = "MergeLevelsTooExpensiveError"


class MergedEnchantedItem(EnchantedItem):
    def __init__(self, left_item_obj, right_item_obj):
        left_item = left_item_obj.item_namespace
        right_item = right_item_obj.item_namespace
        right_item_is_book = right_item == "book"
        right_item_is_left_item = right_item == left_item
        if not right_item_is_left_item:
            if not right_item_is_book:
                left_item_is_book = left_item == "book"
                if not left_item_is_book:
                    raise IncompatibleItemsError()
                else:
                    raise BookNotOnRightError()
        enchantments = combineEnchantments(left_item_obj.enchantments_obj, right_item_obj.enchantments_obj)
        if right_item_is_book:
            merge_levels = enchantments.merge_levels
        else:
            merge_levels = 2 * enchantments.merge_levels
        left_prior_work = left_item_obj.prior_work
        right_prior_work = right_item_obj.prior_work
        prior_work_penalty = priorWork2Penalty(left_prior_work) + priorWork2Penalty(right_prior_work)
        merge_levels += prior_work_penalty
        if merge_levels > MAXIMUM_MERGE_LEVELS:
            raise MergeLevelsTooExpensiveError()
        prior_work = max(left_prior_work, right_prior_work) + 1
        left_cumulative_levels = left_item_obj.cumulative_levels
        right_cumuluative_levels = right_item_obj.cumulative_levels
        cumulative_levels = left_cumulative_levels + right_cumuluative_levels + merge_levels
        left_cumulative_minimum_xp = left_item_obj.cumulative_minimum_xp
        right_cumulative_minimum_xp = right_item_obj.cumulative_minimum_xp
        merge_minimum_xp = experienceFromLevel(merge_levels)
        cumulative_minimum_xp = left_cumulative_minimum_xp + right_cumulative_minimum_xp + merge_minimum_xp
        super().__init__(left_item, enchantments, prior_work, cumulative_levels, cumulative_minimum_xp)
        self.left_item_obj = left_item_obj
        self.right_item_obj = right_item_obj
        self.merge_levels = merge_levels
        self.merge_xp = experienceFromLevel(merge_levels)

    def getInstructions(self):
        left_item_obj = self.left_item_obj
        right_item_obj = self.right_item_obj
        child_item_objs = [left_item_obj, right_item_obj]
        instructions = []
        for child_item in child_item_objs:
            if isinstance(child_item, MergedEnchantedItem):
                child_instructions = child_item.getInstructions()
                instructions.extend(child_instructions)
        merge_levels = self.merge_levels
        merge_xp = self.merge_xp
        prior_work = self.prior_work
        single_instruction = [left_item_obj, right_item_obj, merge_levels, merge_xp, prior_work]
        instructions.append(single_instruction)
        return instructions


def generateEnchantedItems(item_namespace, enchantments, prior_work=0):
    enchanted_item_objs = []
    empty_enchantments_obj = Enchantments([])
    if item_namespace != "book":
        enchanted_tool_obj = EnchantedItem(
            item_namespace,
            empty_enchantments_obj,
            prior_work=prior_work
        )
        enchanted_item_objs.append(enchanted_tool_obj)
    book_namespace = "book"
    for enchantment in enchantments:
        enchantment_namespace = enchantment[0]
        enchantment_level = enchantment[1]
        enchantment_id = ENCHANTMENT2ID[enchantment_namespace]
        enchantment_obj = Enchantment(enchantment_id, enchantment_level)
        enchantments_obj = Enchantments([enchantment_obj])
        enchanted_item_obj = EnchantedItem(book_namespace, enchantments_obj, prior_work=0)
        enchanted_item_objs.append(enchanted_item_obj)
    return enchanted_item_objs


with open('enchanting_data.json') as f:
    data = json.load(f)


class EnchantmentsSelect(discord.ui.Select):
    def __init__(self, item, author):
        temp = [
            discord.SelectOption(
                label=f"{enchant}{f' {max_lvl}' if (max_lvl := int(data['data']['enchants'][enchant]['levelMax'])) > 1 else ''}"
            ) for enchant, metadata in data['data']['enchants'].items()
            if item in metadata['items']
        ]
        super().__init__(
            options=temp,
            min_values=1,
            max_values=min(10, len(temp)),
            placeholder="Choose Enchantments"
        )
        self.item = item
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.respond("You have to run the command yourself to interact with it!", ephemeral=True)
            return

        self.disabled = True
        await interaction.response.edit_message(view=self.view)

        enchants = []
        for value in self.values:
            split_values = value.split(' ')
            enchant_name = split_values[0]

            if len(split_values) == 2:
                lvl = int(split_values[1])
            else:
                lvl = 1

            enchants.append((
                enchant_name,
                lvl
            ))

        response = process(self.item, enchants, 'levels')
        string = ""
        index = 1
        for instruction in response['instructions']:
            # TODO make a function to replace item with emoji (+ enchanted vs unenchanted)
            string += f"{index}. Combine **{instruction[0].item_namespace}**"
            # If item is enchanted, list enchantments
            if instruction[0].enchantments_obj.enchantment_objs:
                enchantments = ""
                for enchantment in instruction[0].enchantments_obj.enchantment_objs:
                    enchantments += str(enchantment.namespace)
                    if enchantment.level > 1:
                        enchantments += f" {enchantment.level}"
                    enchantments += ", "
                string += " (" + enchantments.strip(', ') + ")"

            # TODO make a function to replace item with emoji (+ enchanted vs unenchanted)
            string += f" with **{instruction[1].item_namespace}**"
            # If item is enchanted, list enchantments
            if instruction[1].enchantments_obj.enchantment_objs:
                enchantments = ""
                for enchantment in instruction[1].enchantments_obj.enchantment_objs:
                    enchantments += str(enchantment.namespace)
                    if enchantment.level > 1:
                        enchantments += f" {enchantment.level}"
                    enchantments += ", "
                string += " (" + enchantments.strip(', ') + ")"

            # TODO make this nicer somehow
            string += f"\n-# **Cost**: {instruction[2]} levels ({instruction[3]} xp), **Prior Work Penalty**: {instruction[4]} levels\n"
            index += 1
        enchantments_string = ', '.join((
            f"{enchant}{f' {level}' if level > 1 else ''}"
            for enchant, level in enchants
        ))
        embed = discord.Embed(
            title=f"Enchanting {self.item} with: {enchantments_string}",
            description=string.strip(),
            color=discord.Color.purple()
        )
        embed.set_footer(
            text=f"Total xp levels: {sum([int(instruction[2]) for instruction in response['instructions']])}"
        )
        await interaction.edit_original_response(
            embed=embed,
            view=None,
        )
        # await ctx.respond(string.strip('\n'))


class Enchanting(discord.Cog):

    def __init__(self, bot):
        self.bot = bot
        print(f"** SUCCESSFULLY LOADED {__name__} **")

    @discord.slash_command(
        name="enchanting",
        description="Lookup the best enchanting order for an item",
    )
    async def enchanting(
        self,
        ctx,
        item: discord.commands.Option(
            str,
            description="Item to enchant",
            choices=data['data']['items'],
            required=True,
        ),
    ):
        global ENCHANTMENT2ID, ITEM2ENCHANTMENTS, ENCHANTMENT2WEIGHT, ENCHANTMENT2NAMESPACE, ITEM_NAMESPACES, MAXIMUM_MERGE_LEVELS
        ENCHANTMENT2ID = {}
        ITEM2ENCHANTMENTS = {}
        ENCHANTMENT2WEIGHT = {}
        ENCHANTMENT2NAMESPACE = []
        ITEM_NAMESPACES = data['data']['items']
        MAXIMUM_MERGE_LEVELS = 39

        # enchants = [('unbreaking', 3), ('mending', 1)]

        ITEM2ENCHANTMENTS[item] = []
        enchantment_id = 0
        for enchantment_namespace, enchantment_metadata in data['data']['enchants'].items():
            enchantment_weight = enchantment_metadata["weight"]
            enchantment_items = enchantment_metadata["items"]
            if item in enchantment_items:
                ITEM2ENCHANTMENTS[item].append(enchantment_namespace)
            ENCHANTMENT2ID[enchantment_namespace] = enchantment_id
            ENCHANTMENT2WEIGHT[enchantment_id] = enchantment_weight
            enchantment_id += 1
        ENCHANTMENT2WEIGHT = dict(ENCHANTMENT2WEIGHT)
        ENCHANTMENT2ID = dict(ENCHANTMENT2ID)
        for item, enchantments in ITEM2ENCHANTMENTS.items():
            for index, enchantment in enumerate(enchantments):
                enchantments[index] = ENCHANTMENT2ID[enchantment]
        ITEM2ENCHANTMENTS = dict(ITEM2ENCHANTMENTS)

        # print(ENCHANTMENT2ID)
        # print(ITEM2ENCHANTMENTS)
        # print(ENCHANTMENT2WEIGHT)
        # print(ENCHANTMENT2NAMESPACE)
        # print(ITEM_NAMESPACES)

        # Select enchantments for that item in discord select view
        enchantments_view = discord.ui.View()
        enchantments_view.add_item(EnchantmentsSelect(item, ctx.user))
        await ctx.respond(
            "Select enchantments",
            view=enchantments_view
        )

        # await ctx.defer()

        return


def setup(bot):
    bot.add_cog(Enchanting(bot))

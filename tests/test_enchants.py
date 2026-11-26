"""Tests for the enchantment-ordering algorithms in ``cogs.enchants``."""

import asyncio
from types import SimpleNamespace
from unittest import mock

import pytest

from cogs import enchants
from conftest import FakeContext, FakeInteraction


@pytest.fixture(scope="module", autouse=True)
def initialized_enchanting_globals():
    """Run the command callback once to set up the module's lookup tables."""
    ctx = FakeContext()
    asyncio.run(enchants.Enchanting.enchanting.callback(enchants.Enchanting(None), ctx, "pickaxe"))
    assert ctx.response_content == "Select enchantments"
    assert "unbreaking" in enchants.ENCHANTMENT2ID
    assert "book" in enchants.ITEM_NAMESPACES


def make_enchanted_item(namespace="book", enchantments=(), prior_work=0, levels=0, xp=0):
    return SimpleNamespace(
        item_namespace=namespace,
        enchantments_obj=SimpleNamespace(enchantment_objs=list(enchantments)),
        prior_work=prior_work,
        cumulative_levels=levels,
        cumulative_minimum_xp=xp,
    )


def make_enchantment(id, level):
    return SimpleNamespace(id=id, level=level, levels=level, namespace="test")


class TestCombinations:
    def test_invalid_k(self):
        assert enchants.combinations([1, 2, 3], 0) == []
        assert enchants.combinations([1, 2, 3], 4) == []

    def test_full_and_single_combinations(self):
        assert enchants.combinations([1, 2, 3], 3) == [[1, 2, 3]]
        assert enchants.combinations([1, 2], 1) == [[1], [2]]

    def test_partial_combinations(self):
        assert enchants.combinations([1, 2, 3, 4], 2) == [
            [1, 2], [1, 3], [1, 4], [2, 3], [2, 4], [3, 4],
        ]


class TestNumberChecks:
    @pytest.mark.parametrize(
        ("function", "values"),
        [
            (enchants.isInt, {3: True, 3.0: True, 3.5: False, -2: True}),
            (enchants.isNaturalNumber, {3: True, 0: True, -1: False, 1.5: False}),
            (enchants.isPositiveInt, {1: True, 3.0: True, 0: False, -1: False, 0.5: False}),
        ],
    )
    def test_number_predicates(self, function, values):
        for value, expected in values.items():
            assert function(value) is expected


class TestExperience:
    @pytest.mark.parametrize(
        ("level", "expected"),
        [
            (0, 0),
            (1, 8),
            (16, 263),
            (17, 2.5 * 17 * 17 - 40.5 * 17 + 360),
            (31, 2.5 * 31 * 31 - 40.5 * 31 + 360),
            (32, 4.5 * 32 * 32 - 162.5 * 32 + 2220),
        ],
    )
    def test_experience_from_level(self, level, expected):
        assert enchants.experienceFromLevel(level) == expected

    @pytest.mark.parametrize(
        ("prior_work", "penalty"),
        [(0, 0), (1, 1), (2, 3), (3, 7), (4, 15)],
    )
    def test_prior_work_penalty(self, prior_work, penalty):
        assert enchants.priorWork2Penalty(prior_work) == penalty


class TestEnchantmentObjects:
    def test_enchantment_levels_and_namespace(self):
        enchantment_id = enchants.ENCHANTMENT2ID["unbreaking"]
        enchantment = enchants.Enchantment(enchantment_id, 3)
        assert enchantment.id == enchantment_id
        assert enchantment.level == 3
        assert enchantment.levels == 3 * int(enchants.ENCHANTMENT2WEIGHT[enchantment_id])
        assert enchantment.namespace == "unbreaking"

    @pytest.mark.parametrize("level", [0, -1, 1.5])
    def test_enchantment_rejects_invalid_level(self, level):
        with pytest.raises(ValueError, match="level must be positive integer"):
            enchants.Enchantment(enchants.ENCHANTMENT2ID["unbreaking"], level)

    def test_enchantment_rejects_unknown_id(self):
        with pytest.raises(ValueError, match="invalid enchantment name"):
            enchants.Enchantment(9999, 1)

    def test_enchantments_sums_levels_and_validates_types(self):
        enchantment = enchants.Enchantment(enchants.ENCHANTMENT2ID["mending"], 1)
        collection = enchants.Enchantments([enchantment], merge_levels=5)
        assert collection.levels == enchantment.levels
        assert collection.merge_levels == 5
        with pytest.raises(TypeError, match="each enchantment must be of type Enchantment"):
            enchants.Enchantments(["not an enchantment"])

    def test_combine_enchantment_same_and_different_ids(self):
        unbreaking_id = enchants.ENCHANTMENT2ID["unbreaking"]
        mending_id = enchants.ENCHANTMENT2ID["mending"]
        first = enchants.Enchantment(unbreaking_id, 2)
        second = enchants.Enchantment(unbreaking_id, 2)
        combined = enchants.combineEnchantment(first, second)
        assert len(combined.enchantment_objs) == 1
        assert combined.enchantment_objs[0].level == 3

        uneven = enchants.combineEnchantment(first, enchants.Enchantment(unbreaking_id, 1))
        assert uneven.enchantment_objs[0].level == 2

        different = enchants.combineEnchantment(first, enchants.Enchantment(mending_id, 1))
        assert [obj.id for obj in different.enchantment_objs] == [unbreaking_id, mending_id]

    def test_combine_enchantments_merges_common_id(self):
        unbreaking_id = enchants.ENCHANTMENT2ID["unbreaking"]
        left = enchants.Enchantments([enchants.Enchantment(unbreaking_id, 2)])
        right = enchants.Enchantments([enchants.Enchantment(unbreaking_id, 2)])
        result = enchants.combineEnchantments(left, right)
        assert result.merge_levels == 3 * int(enchants.ENCHANTMENT2WEIGHT[unbreaking_id])
        assert len(result.enchantment_objs) == 1


class TestEnchantedItems:
    def test_generate_enchanted_items(self):
        items = enchants.generateEnchantedItems("pickaxe", [("unbreaking", 3), ("mending", 1)])
        assert len(items) == 3
        assert items[0].item_namespace == "pickaxe"
        assert items[0].enchantments_obj.enchantment_objs == []
        assert [item.item_namespace for item in items[1:]] == ["book", "book"]

        books_only = enchants.generateEnchantedItems("book", [("unbreaking", 3)])
        assert len(books_only) == 1
        assert books_only[0].item_namespace == "book"

    def test_invalid_namespace_and_incompatible_enchantment(self):
        empty = enchants.Enchantments([])
        with pytest.raises(enchants.InvalidItemNameError):
            enchants.EnchantedItem("not_an_item", empty)

        channeling = enchants.Enchantment(enchants.ENCHANTMENT2ID["channeling"], 1)
        with pytest.raises(enchants.InvalidEnchantmentError):
            enchants.EnchantedItem("pickaxe", enchants.Enchantments([channeling]))

    @pytest.mark.parametrize("prior_work", [-1, 1.5])
    def test_invalid_prior_work(self, prior_work):
        with pytest.raises(ValueError, match="prior work must be non-negative integer"):
            enchants.EnchantedItem("book", enchants.Enchantments([]), prior_work=prior_work)

    def test_merge_requires_same_item_or_book_on_right(self):
        pickaxe = make_enchanted_item("pickaxe")
        chestplate = make_enchanted_item("chestplate")
        book = make_enchanted_item("book")

        with pytest.raises(enchants.IncompatibleItemsError):
            enchants.combineEnchantedItem(pickaxe, chestplate)
        with pytest.raises(enchants.BookNotOnRightError):
            enchants.combineEnchantedItem(book, pickaxe)

    def test_merge_updates_prior_work_levels_and_xp(self):
        empty = enchants.Enchantments([])
        left = enchants.EnchantedItem("pickaxe", empty, prior_work=1, cumulative_levels=5, cumulative_minimum_xp=10)
        right = enchants.EnchantedItem("pickaxe", empty)
        merged = enchants.combineEnchantedItem(left, right)
        assert merged.prior_work == 2
        assert merged.merge_levels == enchants.priorWork2Penalty(1)
        assert merged.cumulative_levels == 5 + merged.merge_levels
        assert merged.cumulative_minimum_xp == 10 + enchants.experienceFromLevel(merged.merge_levels)
        instructions = merged.getInstructions()
        assert len(instructions) == 1
        assert instructions[0][4] == 2

    def test_merge_rejects_levels_above_maximum(self):
        empty = enchants.Enchantments([])
        left = enchants.EnchantedItem("pickaxe", empty)
        right = enchants.EnchantedItem("pickaxe", empty)
        with mock.patch.object(enchants, "combineEnchantments", return_value=SimpleNamespace(
            enchantment_objs=[], merge_levels=40
        )):
            with pytest.raises(enchants.MergeLevelsTooExpensiveError):
                enchants.combineEnchantedItem(left, right)


class TestCheapestSelection:
    def test_compare_cheapest_prefers_fewer_levels(self):
        cheap = make_enchanted_item(levels=2)
        expensive = make_enchanted_item(levels=5)
        assert enchants.compareCheapest(cheap, expensive)[0] is cheap
        assert enchants.compareCheapest(expensive, cheap)[0] is cheap

    def test_selection_by_levels_and_first_prior_work(self):
        low_levels = make_enchanted_item(levels=2, prior_work=3)
        low_prior_work = make_enchanted_item(levels=8, prior_work=0)
        dictionary = {3: low_levels, 0: low_prior_work}
        assert enchants.cheapestItemFromDictionaryByLevels(dictionary) is low_levels
        # This helper keeps the first entry, not the numerically smallest key.
        assert enchants.cheapestItemFromDictionaryByPriorWork(dictionary) is low_levels
        assert enchants.cheapestItemFromDictionaryByPriorWork(
            {0: low_prior_work, 3: low_levels}
        ) is low_prior_work

    def test_remove_expensive_candidates(self):
        cheap = make_enchanted_item(levels=2)
        expensive = make_enchanted_item(levels=5)
        result = enchants.removeExpensiveCandidatesFromDictionary({9: expensive, 1: cheap})
        assert result == {9: expensive, 1: cheap}  # already in ascending order
        assert enchants.removeExpensiveCandidatesFromDictionary({1: cheap, 9: expensive}) == {1: cheap}

    def test_cheapest_items_from_list(self):
        item = make_enchanted_item(levels=1, prior_work=0)
        assert enchants.cheapestItemsFromList([item]) == {0: item}

        cheap = make_enchanted_item(levels=1, prior_work=0)
        expensive = make_enchanted_item(levels=5, prior_work=0)
        with mock.patch.object(enchants, "cheapestItemFromItems2", return_value=cheap):
            assert enchants.cheapestItemsFromList([expensive, cheap]) == {0: cheap}


class TestProcess:
    def test_process_returns_instructions(self):
        result = enchants.process("pickaxe", [("unbreaking", 3), ("mending", 1)])
        assert result["msg"] == "complete"
        assert result["item_obj"] is not None
        assert result["instructions"]
        assert all(len(instruction) == 5 for instruction in result["instructions"])

    def test_process_supports_prior_work_mode(self):
        with mock.patch.object(
            enchants, "cheapestItemFromDictionaryByPriorWork",
            wraps=enchants.cheapestItemFromDictionaryByPriorWork,
        ) as select:
            result = enchants.process("pickaxe", [("mending", 1)], "prior_work")
        select.assert_called_once()
        assert result["item_obj"] is not None


class TestEnchantmentsSelect:
    async def test_other_users_cannot_interact(self):
        author = SimpleNamespace(id=1)
        view = enchants.EnchantmentsSelect("pickaxe", author)
        view._selected_values = ["unbreaking 3"]
        interaction = FakeInteraction(user=SimpleNamespace(id=2))
        await view.callback(interaction)
        assert interaction.calls_named("respond")[0][2]["ephemeral"] is True
        assert not interaction.calls_named("edit_original_response")

    async def test_selection_builds_embed_with_instructions(self):
        author = SimpleNamespace(id=1)
        view = enchants.EnchantmentsSelect("pickaxe", author)
        view._selected_values = ["unbreaking 3", "mending"]
        interaction = FakeInteraction(user=author)
        instruction_item = make_enchanted_item(
            "book", [make_enchantment(enchants.ENCHANTMENT2ID["unbreaking"], 3)], levels=5
        )
        instructions = [[instruction_item, instruction_item, 5, 18, 1]]
        with mock.patch.object(enchants, "process", return_value={
            "msg": "complete", "item_obj": None, "instructions": instructions,
        }) as process:
            await view.callback(interaction)
        process.assert_called_once_with("pickaxe", [("unbreaking", 3), ("mending", 1)], "levels")
        embed = interaction.calls_named("edit_original_response")[0][2]["embed"]
        assert "Enchanting pickaxe with: unbreaking 3, mending" == embed.title
        assert "Combine **book**" in embed.description
        assert "Cost" in embed.description
        assert embed.footer.text == "Total xp levels: 5"
        assert interaction.calls_named("response.edit_message")

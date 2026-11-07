"""形态 / 配色两轴的口径测试。

参考上游 ``ElliottZhao666666/rocom-codex-pets-gen`` 的
``references/color-appearance.md``：模型形态与配色是两条独立轴，配色共九类，
污染与异色互斥，黑白与异色黑白是两类。
"""

from app.adapters.petvariant import COLOR_TYPES, classify, variant_summary


def test_nine_color_types_present():
    assert len(COLOR_TYPES) == 9
    assert set(COLOR_TYPES) == {
        "normal", "normal_glassy", "normal_black_white", "normal_seasonal",
        "pollution", "shiny", "shiny_glassy", "shiny_seasonal", "shiny_black_white",
    }


def test_plain_name_is_normal_without_form():
    result = classify("影狸")
    assert result["color_type"] == "normal"
    assert result["form"] == ""
    assert result["is_shiny"] is False and result["is_polluted"] is False


def test_model_form_is_kept_as_form():
    result = classify("千棘盔（磨损的样子）")
    assert result["base_name"] == "千棘盔"
    assert result["form"] == "磨损的样子"
    assert result["color_type"] == "normal"


def test_pollution_is_a_color_not_a_form():
    result = classify("波波螺（被污染的样子）")
    assert result["base_name"] == "波波螺"
    assert result["form"] == ""
    assert result["form_raw"] == "被污染的样子"
    assert result["color_type"] == "pollution"
    assert result["is_polluted"] is True


def test_shiny_family():
    assert classify("机械方方（异色）")["color_type"] == "shiny"
    assert classify("机械方方（异色炫彩）")["color_type"] == "shiny_glassy"
    assert classify("机械方方（异色黑白炫彩）")["color_type"] == "shiny_black_white"
    assert classify("机械方方（异色赛季炫彩）")["color_type"] == "shiny_seasonal"


def test_black_white_is_not_shiny():
    result = classify("机械方方（黑白炫彩）")
    assert result["color_type"] == "normal_black_white"
    assert result["is_shiny"] is False


def test_season_number_is_parsed():
    result = classify("机械方方（S3赛季炫彩）")
    assert result["color_type"] == "normal_seasonal"
    assert result["season"] == 3


def test_pollution_wins_over_shiny_and_reports_conflict():
    result = classify("机械方方（污染异色）")
    assert result["color_type"] == "pollution"
    assert result["notes"]


def test_variant_summary_keeps_color_order_and_drops_zero():
    summary = variant_summary(["影狸", "波波螺（被污染的样子）", "机械方方（异色）", "机械方方（异色）"])
    assert list(summary) == ["normal", "pollution", "shiny"]
    assert summary == {"normal": 1, "pollution": 1, "shiny": 2}

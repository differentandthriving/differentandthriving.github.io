from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    path = ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def luminance(hex_color: str) -> float:
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(first: str, second: str) -> float:
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


class SiteMarkup(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.section_ids: list[str] = []
        self.headings: list[str] = []
        self.hrefs: list[str] = []
        self.classes: list[str] = []
        self._in_heading = False
        self._heading_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "section" and attributes.get("id"):
            self.section_ids.append(attributes["id"] or "")
        if tag in {"h2", "h3"}:
            self._in_heading = True
            self._heading_buffer = []
        if attributes.get("href"):
            self.hrefs.append(attributes["href"] or "")
        if attributes.get("class"):
            self.classes.append(attributes["class"] or "")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h2", "h3"} and self._in_heading:
            self.headings.append(" ".join("".join(self._heading_buffer).split()))
            self._in_heading = False

    def handle_data(self, data: str) -> None:
        if self._in_heading:
            self._heading_buffer.append(data)


class ProfileSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = read_text("_config.yml")
        cls.css = read_text("assets/css/custom-styles.css")
        cls.index = read_text("index.html")
        cls.cname = read_text("CNAME").strip()
        match = re.match(r"---\s*\n(.*?)\n---\s*\n(.*)\Z", cls.index, re.DOTALL)
        cls.front_matter = match.group(1) if match else ""
        cls.body = match.group(2) if match else ""
        cls.markup = SiteMarkup()
        cls.markup.feed(cls.body)

    def test_jekyll_uses_beautiful_jekyll_with_only_remote_theme_plugin(self) -> None:
        self.assertIn("remote_theme: daattali/beautiful-jekyll@6.0.1", self.config)
        self.assertIn("- jekyll-remote-theme", self.config)
        plugins = re.search(r"^plugins:\s*\n((?:\s+-\s+[^\n]+\n?)+)", self.config, re.MULTILINE)
        self.assertIsNotNone(plugins, "Configure the Jekyll plugin list explicitly")
        self.assertEqual(
            re.findall(r"^\s+-\s+([^\s#]+)", plugins.group(1), re.MULTILINE),
            ["jekyll-remote-theme"],
        )
        self.assertIn('title: "Tiffany Gibson"', self.config)
        self.assertIn('url: "https://differentandthriving.com"', self.config)
        self.assertIn('baseurl: ""', self.config)
        self.assertIn('navbar-col: "#4D7166"', self.config)
        self.assertIn('navbar-text-col: "#E8F0EC"', self.config)

    def test_homepage_uses_the_selected_hero_and_approved_headline(self) -> None:
        self.assertIn("layout: profile-home", self.front_matter)
        self.assertIn('cover-img: "/assets/img/brain-ribbons.jpg"', self.front_matter)
        self.assertIn('share-img: "/assets/img/brain-ribbons.jpg"', self.front_matter)
        self.assertIn('hero_line_one: "Different & thriving"', self.front_matter)
        self.assertTrue(
            (ROOT / "assets/img/brain-ribbons.jpg").is_file(),
            "The selected hero artwork must exist in the repository",
        )

    def test_body_copy_uses_mildly_expanded_tracking_and_leading(self) -> None:
        selector = ".profile-hero__copy,\n.profile-section p:not(.profile-eyebrow),\n.profile-faq summary {"
        self.assertIn(selector, self.css)
        style = self.css.split(selector, 1)[1].split("}", 1)[0]
        self.assertIn("letter-spacing: 0.02em;", style)
        self.assertIn("line-height: 1.75;", style)

    def test_pullquotes_are_placed_below_their_relevant_images(self) -> None:
        def section(section_id: str) -> str:
            start = self.body.index(f'<section id="{section_id}"')
            end = self.body.index("</section>", start)
            return self.body[start:end]

        about = section("about")
        about_image_column = about.split('<div class="col-lg-6 offset-lg-1">', 1)[0]
        self.assertLess(about_image_column.index("brain-types.svg"), about_image_column.index('class="profile-pullquote"'))
        self.assertIn("You're starting in a place of overwhelm.", about_image_column)
        self.assertIn("<b>That's okay.</b>", about_image_column)
        self.assertIn('aria-hidden="true"', about_image_column)
        self.assertEqual(about.count("You're starting in a place of overwhelm."), 2)

        approach = section("approach")
        approach_image_column = approach.split('<div class="col-lg-5 offset-lg-1">', 1)[1]
        self.assertLess(approach_image_column.index("brain-colors_1920.png"), approach_image_column.index('class="profile-pullquote"'))
        self.assertIn("the mind that made me unique also came with", approach_image_column)
        self.assertIn("<b><em>untold strengths, which I had been using all along</em></b>", approach_image_column)
        self.assertIn('aria-hidden="true"', approach_image_column)
        self.assertEqual(approach.count("the mind that made me unique also came with"), 2)

    def test_pullquotes_have_large_legible_typography(self) -> None:
        self.assertIn(".profile-pullquote {", self.css)
        self.assertIn(".profile-section .profile-pullquote p {", self.css)
        self.assertIn("font-size: clamp(1.25rem, 1.65vw, 1.7rem);", self.css)
        self.assertIn("line-height: 1.45;", self.css)
        self.assertIn("border-left: 4px solid var(--profile-rose);", self.css)
        self.assertIn(".profile-section--rose .profile-pullquote", self.css)

    def test_garden_immersion_uses_direct_image_overlay_and_color_fields(self) -> None:
        self.assertIn(".profile-hero", self.css)
        self.assertIn("linear-gradient(90deg", self.css)
        self.assertIn("min-height: 80vh", self.css)
        self.assertIn('url("/assets/img/brain-ribbons.jpg")', self.css)
        for section_class in ["profile-section--coastal", "profile-section--rose"]:
            self.assertIn(section_class, self.body)
        for image in ["brain-types.svg", "brain-colors_1920.png"]:
            self.assertIn(image, self.body)
            self.assertTrue((ROOT / "assets/img" / image).is_file())

    def test_garden_immersion_hero_has_the_mockup_text_and_cta(self) -> None:
        self.assertIn("layout: profile-home", self.front_matter)
        layout = read_text("_layouts/profile-home.html")
        self.assertIn("layout: base", layout)
        for expected in ["page.hero_eyebrow", "page.hero_line_one", "page.hero_line_two", "page.hero_copy", "page.hero_button_text", "page.hero_button_href"]:
            self.assertIn(expected, layout)
        self.assertIn("{{ page.hero_line_one | escape }} <br />", layout)
        self.assertIn('href="{{ page.hero_button_href | escape }}"', layout)
        for expected in [
            'hero_eyebrow: "Neurodiversity family coaching"',
            'hero_line_one: "Different & thriving"',
            'hero_copy: "Compassionate, practical support for families navigating life with a neurodivergent child."',
            'hero_button_text: "Explore coaching"',
            'hero_button_href: "#coaching"',
        ]:
            self.assertIn(expected, self.front_matter)

    def test_top_navbar_matches_garden_immersion(self) -> None:
        self.assertIn('navbar-col: "#4D7166"', self.config)
        self.assertIn('navbar-text-col: "#E8F0EC"', self.config)
        for link in ['About: "/#about"', 'Coaching: "/#coaching"', 'Compare: "/design-versions/"']:
            self.assertIn(link, self.config)
        self.assertIn(".navbar-custom.fixed-top", self.css)
        self.assertIn("background-color: var(--profile-garden)", self.css)

    def test_homepage_shell_matches_garden_margins_and_typography(self) -> None:
        layout = read_text("_layouts/profile-home.html")
        hero = layout.split("</header>", 1)[0]
        self.assertIn('<div class="container">', hero)
        self.assertNotIn('class="row"', hero)
        self.assertNotIn("col-lg-8", hero)
        self.assertIn('<main id="main-content" role="main">', layout)
        self.assertNotIn("container-fluid", layout)

        self.assertIn("padding: 1rem 15px;", self.css)
        self.assertIn("calc((100vw - 1140px) / 2 + 15px)", self.css)
        self.assertRegex(self.css, r"\.navbar-custom \.navbar-brand \{[^}]*text-transform: uppercase")
        self.assertRegex(self.css, r"\.navbar-custom \.navbar-brand \{[^}]*letter-spacing: 0\.06em")
        self.assertRegex(self.css, r"\.navbar-custom \.navbar-nav \.nav-link \{[^}]*font-weight: 400")
        self.assertRegex(self.css, r"\.profile-hero h1 \{[^}]*font-weight: 500")
        self.assertRegex(self.css, r"\.profile-section h2 \{[^}]*font-weight: 500")
        self.assertRegex(self.css, r"\.profile-service-panel h3 \{[^}]*font-weight: 500")
        self.assertIn("margin-bottom: 1rem;", self.css)
        self.assertIn("margin: 0 0 0.5rem;", self.css)
        self.assertIn("font-size: 2rem;", self.css)
        self.assertNotIn("font-size: clamp(2rem, 3.5vw, 3rem);", self.css)

    def test_body_sections_follow_garden_immersion_composition(self) -> None:
        def section(section_id: str) -> str:
            start = self.body.index(f'<section id="{section_id}"')
            end = self.body.index("</section>", start)
            return self.body[start:end]

        about = section("about")
        self.assertLess(about.index("brain-types.svg"), about.index("Coaching"))
        self.assertLess(about.index("brain-types.svg"), about.index('class="profile-pullquote"'))
        coaching = section("coaching")
        self.assertLess(coaching.index("Book an appointment"), coaching.index("profile-service-panel panel"))
        self.assertEqual(coaching.count('class="profile-service-panel panel"'), 3)
        who = section("who-i-support")
        self.assertLess(who.index("Topics"), who.index("child-brain-puzzle_1920.png"))
        self.assertIn("child-brain-puzzle_1920.png", who)
        approach = section("approach")
        self.assertLess(approach.index("Tiffany"), approach.index("brain-colors_1920.png"))
        self.assertLess(approach.index("brain-colors_1920.png"), approach.index('class="profile-pullquote"'))

    def test_services_use_the_rose_opening_panel_shape(self) -> None:
        self.assertEqual(self.body.count('class="profile-service-panel panel"'), 3)
        self.assertIn(".profile-service-panel.panel", self.css)
        self.assertIn("border-radius: 0 2rem 0 2rem;", self.css)
        self.assertIn("background: rgba(255, 255, 255, 0.09);", self.css)
        self.assertIn(".profile-service-panel h3", self.css)

    def test_profile_sections_follow_current_page_order(self) -> None:
        self.assertEqual(
            self.markup.section_ids,
            ["about", "coaching", "who-i-support", "approach", "faq"],
        )
        for heading in [
            "Coaching",
            "Book an appointment",
            "Topics",
            "Tiffany",
            "Questions",
        ]:
            self.assertIn(heading, self.markup.headings)

    def test_explicit_rate_faq_and_contact_placeholders_remain_visible(self) -> None:
        for placeholder in [
            "[Rate €]",
            "[FAQ question placeholder]",
            "[FAQ answer placeholder]",
            "[Contact details placeholder:",
        ]:
            self.assertIn(placeholder, self.body)
        self.assertNotIn("mailto:", self.body.lower())

    def test_brand_colors_and_custom_css_are_wired_to_the_theme(self) -> None:
        for color in ["#E8F0EC", "#263D38", "#4D7166", "#A64F67", "#3E6D7A"]:
            self.assertIn(color, self.config)
            self.assertIn(color, self.css)
        self.assertIn("/assets/css/custom-styles.css", self.config)
        self.assertTrue(any("container" in value for value in self.markup.classes))
        self.assertTrue(any("row" in value for value in self.markup.classes))
        self.assertIn("@media (max-width: 767.98px)", self.css)
        self.assertIn(".profile-hero { min-height: 70vh; }", self.css)

    def test_local_and_github_builds_use_the_minimal_versioned_stack(self) -> None:
        gemfile = read_text("Gemfile")
        workflow = read_text(".github/workflows/pages.yml")
        self.assertIn('gem "jekyll", "4.4.1"', gemfile)
        self.assertIn('gem "jekyll-remote-theme", "0.6.3"', gemfile)
        self.assertIn('ruby-version: "3.3.13"', workflow)
        self.assertIn("bundler-cache: true", workflow)
        self.assertIn("bundle exec jekyll build", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("if: github.ref == 'refs/heads/main'", workflow)
        for action in [
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            "ruby/setup-ruby@b3aaceaef7e0ee231b499e7b5f49c03fc1d32199",
            "actions/configure-pages@45bfe0192ca1faeb007ade9deae92b16b8254a0d",
            "actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9",
            "actions/deploy-pages@368f82528645a54fb793d4d04e342629a3f51346",
        ]:
            self.assertIn(action, workflow)

    def test_text_color_pairs_meet_wcag_aa_for_normal_text(self) -> None:
        pairs = [
            ("#263D38", "#E8F0EC"),
            ("#4D7166", "#E8F0EC"),
            ("#A64F67", "#E8F0EC"),
            ("#3E6D7A", "#E8F0EC"),
            ("#E8F0EC", "#4D7166"),
            ("#E8F0EC", "#263D38"),
            ("#F0C9D2", "#263D38"),
            ("#FFFFFF", "#A64F67"),
            ("#FFFFFF", "#873C52"),
            ("#FFFFFF", "#4D7166"),
        ]
        for foreground, background in pairs:
            with self.subTest(foreground=foreground, background=background):
                self.assertGreaterEqual(contrast_ratio(foreground, background), 4.5)

    def test_nav_hover_and_focus_states_keep_clear_contrast(self) -> None:
        self.assertIn(".navbar-custom .navbar-nav .nav-link:hover", self.css)
        self.assertIn(".navbar-custom .navbar-brand:hover { color: #fff; text-decoration: underline; }", self.css)
        self.assertIn("outline-color: var(--profile-surface);", self.css)

    def test_planning_artifacts_stay_local_and_out_of_the_published_site(self) -> None:
        gitignore = read_text(".gitignore")
        expected = [
            "2026-11-14_134026-neurodiversity-family-coach-profile.md",
            "neurodiversity-coach-color-options.html",
            "neurodiversity-coach-color-options-round-2.html",
            "neurodiversity-coach-color-options-round-2.svg",
        ]
        self.assertIn("/plans/", gitignore)
        self.assertIn("  - plans/", self.config)
        for name in expected:
            with self.subTest(plan=name):
                self.assertTrue((ROOT / "plans" / name).is_file())

    def test_custom_domain_is_configured(self) -> None:
        self.assertEqual(self.cname, "differentandthriving.com")


if __name__ == "__main__":
    unittest.main()

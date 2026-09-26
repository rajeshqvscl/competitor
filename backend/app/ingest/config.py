"""Registry of ingestible companies: website + annual-report discovery config."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CompanyCfg:
    slug: str
    name: str
    website: str
    # Path hints on the website to discover annual-report PDFs (relative or absolute).
    ir_paths: tuple[str, ...] = ()
    # Direct PDF URLs (pinned) — used when IR page discovery fails or is flaky.
    report_urls: tuple[str, ...] = ()
    # Start paths for product/brand page discovery (relative to website root).
    product_paths: tuple[str, ...] = ("/products", "/product", "/brands", "/our-products")
    # About / company overview page path.
    about_path: str = "/about"
    # Distributor / partner page path (None if site has no such page).
    distributor_paths: tuple[str, ...] = ("/distributors", "/dealer", "/partners", "/channel-partners")
    # Site-specific CSS/selector overrides for the generic website adapter.
    # Keys: "brand_items", "product_items", "product_name", "product_price", ...
    overrides: dict[str, str] = field(default_factory=dict)

    @property
    def base_url(self) -> str:
        return self.website.rstrip("/")


COMPANIES: tuple[CompanyCfg, ...] = (
    CompanyCfg(
        slug="amul",
        name="Amul (GCMMF)",
        website="https://www.amul.com",
        # GCMMF is a cooperative — public AR PDFs are sparse; about/org pages carry overview.
        ir_paths=("/m/gcmmf", "/m/organisation", "/pages/about-us"),
        product_paths=("/products", "/pages/all-products", "/milk-and-dairy-products"),
        about_path="/pages/about-us",
        distributor_paths=("/pages/distributors", "/distributors"),
    ),
    CompanyCfg(
        slug="mother-dairy",
        name="Mother Dairy",
        website="https://www.motherdairy.com",
        # Private (NDDB sub) — Annual Return PDFs, not listed-company AR.
        ir_paths=("/FooterTemplate/AnnualReturn2025", "/know-us/annual-return"),
        report_urls=(
            "https://www.motherdairy.com/AnnualReturn2024.pdf",
        ),
        product_paths=("/products", "/our-products", "/know-us/products"),
        about_path="/know-us/about-us",
    ),
    CompanyCfg(
        slug="nestle-india",
        name="Nestle India",
        website="https://www.nestle.in",
        ir_paths=("/investors/stockandfinancials/annualreports", "/investors"),
        report_urls=(
            # Nestlé India AR 2023-24 (15-month FY)
            "https://ro.factory.nestle.com/sites/g/files/pydnoa501/files/2025-05/Annual-Report-2023-24.pdf",
        ),
        product_paths=("/products", "/brands"),
        about_path="/about-us",
    ),
    CompanyCfg(
        slug="heritage-foods",
        name="Heritage Foods",
        website="https://www.heritagefoods.in",
        ir_paths=("/annualreport", "/investors", "/investor-relations"),
        report_urls=(
            "https://www.heritagefoods.in/uploads/investors/pdf/17515278770Annual_Report_2024-25_(1).pdf",
        ),
        product_paths=("/products", "/our-products"),
        about_path="/about-us",
    ),
    CompanyCfg(
        slug="verka",
        name="Verka (Milkfed)",
        website="https://verka.coop",
        # Cooperative — no reliable public AR PDF; product/network pages useful.
        ir_paths=("/home", "/about"),
        product_paths=("/products", "/our-products", "/networks"),
        about_path="/home",
    ),
    CompanyCfg(
        slug="dodla-dairy",
        name="Dodla Dairy",
        website="https://dodladairy.com",
        ir_paths=("/investor-corner/annual-reports", "/investor-corner", "/document-tag/annual-reports"),
        report_urls=(
            "https://dodladairy.com/wp-content/uploads/2024/06/Dodla-AR-2024.pdf",
        ),
        product_paths=("/products", "/our-products"),
        about_path="/about-us",
    ),
    CompanyCfg(
        slug="britannia",
        name="Britannia Industries",
        website="https://www.britannia.co.in",
        ir_paths=("/investors/financial-performance/annual-report", "/investors"),
        report_urls=(
            "https://media.britannia.co.in/Britannia_Industries_Limited_Annual_Report_2025_26_30348b56b6.pdf",
        ),
        product_paths=("/products", "/brands", "/our-brands"),
        about_path="/about-us",
    ),
    CompanyCfg(
        slug="parag-milk",
        name="Parag Milk Foods",
        # Correct domain (paragmilks.com was wrong)
        website="https://www.paragmilkfoods.com",
        ir_paths=("/about-us.php/investors.php", "/investors", "/chairman.php/investors.php"),
        product_paths=("/products", "/our-products", "/brands"),
        about_path="/about-us",
    ),
    CompanyCfg(
        slug="hatsun",
        name="Hatsun Agro",
        # Investor site is hap.in (hatsun.com redirects)
        website="https://www.hap.in",
        ir_paths=("/annual-report.php", "/investor-corner", "/"),
        report_urls=(
            "https://www.hap.in/pdf/annualreport/ANNUAL_REPORT_2023.pdf",
        ),
        product_paths=("/products", "/our-products", "/brands"),
        about_path="/about-us.php",
    ),
    CompanyCfg(
        slug="dudhsagar",
        name="Dudhsagar Dairy",
        # Correct TLD (.coop, not .com)
        website="https://dudhsagardairy.coop",
        ir_paths=("/media/annual-reports", "/about-us/overview"),
        product_paths=("/dairy/products", "/products"),
        about_path="/about-us/overview",
    ),
    CompanyCfg(
        slug="warana",
        name="Warana Dairy",
        website="https://www.warana.com",
        product_paths=("/products", "/our-products"),
        about_path="/about-us",
    ),
    CompanyCfg(
        slug="milma",
        name="Milma",
        website="https://milma.com",
        # Noticeboard hosts AR PDFs historically
        ir_paths=("/noticeboard", "/about/aboutus"),
        product_paths=("/products", "/our-products"),
        about_path="/about/aboutus",
    ),
    CompanyCfg(
        slug="nandini",
        name="Nandini (KMF)",
        website="https://www.kmf.co.in",
        ir_paths=("/annual-report", "/about-us", "/"),
        product_paths=("/products", "/our-products"),
        about_path="/about-us",
    ),
    CompanyCfg(
        slug="gowardhan",
        name="Govardhan Dairy",
        # Gowardhan is a Parag brand; standalone site may be minimal
        website="https://www.gowardhan.com",
        product_paths=("/products", "/our-products"),
        about_path="/about-us",
    ),
    CompanyCfg(
        slug="akshayakalpa",
        name="Akshayakalpa",
        # Correct domain (.org, not .com) — startup, no public AR
        website="https://akshayakalpa.org",
        product_paths=("/products", "/shop", "/collections"),
        about_path="/about",
    ),
)


def get_company(slug: str) -> CompanyCfg | None:
    slug = slug.lower().strip()
    for c in COMPANIES:
        if c.slug == slug:
            return c
    return None


def all_slugs() -> list[str]:
    return [c.slug for c in COMPANIES]

"""
SubSentinel AI - NLP & Transaction Pattern Recognition Engine
Specialized for Recurring Charge Identification, Vampire Cost Detection, and Privacy-Safe Transaction Scrubbing.
"""

import re
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple

# Pre-defined known subscription merchant catalog with canonical metadata,
# cancellation complexity, TOS rules, and known dark patterns.
MERCHANT_CATALOG = {
    "netflix": {
        "name": "Netflix",
        "category": "Streaming Video",
        "canonical_name": "Netflix Inc.",
        "icon": "film",
        "color": "#E50914",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "Cancel anytime online. Access continues until the end of current billing period. No prorated refunds.",
        "portal_url": "https://www.netflix.com/youraccount",
        "dark_pattern_rating": "Low",
        "dark_pattern_notes": "Clean self-serve cancellation flow, 2-step confirmation."
    },
    "spotify": {
        "name": "Spotify Premium",
        "category": "Streaming Music",
        "canonical_name": "Spotify AB",
        "icon": "music",
        "color": "#1DB954",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "Can cancel anytime in Account settings. Reverts to Free tier after billing period expires.",
        "portal_url": "https://www.spotify.com/account/subscription/",
        "dark_pattern_rating": "Medium",
        "dark_pattern_notes": "Offers 3-month discount retention pitch prior to final click."
    },
    "adobe": {
        "name": "Adobe Creative Cloud",
        "category": "Design & Productivity",
        "canonical_name": "Adobe Systems Inc.",
        "icon": "palette",
        "color": "#FF0000",
        "cancellation_method": "agent_assisted_negotiation",
        "tos_summary": "Annual plan paid monthly carries 50% remaining contract early termination fee unless cancelled within 14 days of start.",
        "portal_url": "https://account.adobe.com/plans",
        "dark_pattern_rating": "High",
        "dark_pattern_notes": "Famous early termination fee trap and multi-screen retention maze."
    },
    "amazon_prime": {
        "name": "Amazon Prime",
        "category": "E-Commerce & Media",
        "canonical_name": "Amazon.com Inc.",
        "icon": "shopping-cart",
        "color": "#FF9900",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "Refund eligible for unused benefits. Multi-click 'End Membership' flow.",
        "portal_url": "https://www.amazon.com/mc/manage",
        "dark_pattern_rating": "High",
        "dark_pattern_notes": "FTC-challenged 4-page 'Iliad' retention sequence."
    },
    "gym_fit": {
        "name": "Equinox / Planet Fitness",
        "category": "Health & Fitness",
        "canonical_name": "Global Fitness Brands",
        "icon": "activity",
        "color": "#6366F1",
        "cancellation_method": "agent_legal_dispatch",
        "tos_summary": "Requires in-person visit or certified registered mail with 30-day advance notice under contract clause 14B.",
        "portal_url": "https://www.planetfitness.com/about-planet-fitness/contact-us",
        "dark_pattern_rating": "Extreme",
        "dark_pattern_notes": "Forced physical presence or certified mail requirement; dark pattern prohibited by FTC Click-to-Cancel rules."
    },
    "openai": {
        "name": "OpenAI ChatGPT Plus",
        "category": "AI Services",
        "canonical_name": "OpenAI LLC",
        "icon": "cpu",
        "color": "#10A37F",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "Monthly auto-renewal. Access remains active through end of billing cycle.",
        "portal_url": "https://chat.openai.com/#settings/DataControls",
        "dark_pattern_rating": "Low",
        "dark_pattern_notes": "Straightforward Stripe billing portal."
    },
    "aws": {
        "name": "Amazon Web Services (AWS)",
        "category": "Cloud Infrastructure",
        "canonical_name": "Amazon Web Services Inc.",
        "icon": "cloud",
        "color": "#EC7211",
        "cancellation_method": "agent_variable_cap",
        "tos_summary": "Variable consumption billing. Closing account requires terminating all active EC2/RDS instances to halt accrual.",
        "portal_url": "https://console.aws.amazon.com/billing/home#/account",
        "dark_pattern_rating": "Medium",
        "dark_pattern_notes": "Orphaned volumes and elastic IPs continue accruing micro-charges."
    },
    "nytimes": {
        "name": "The New York Times",
        "category": "News & Publishing",
        "canonical_name": "The New York Times Co.",
        "icon": "book-open",
        "color": "#000000",
        "cancellation_method": "agent_assisted_negotiation",
        "tos_summary": "Introductory rate jumps to standard $25/mo after promo period. Online cancellation available in most jurisdictions.",
        "portal_url": "https://www.nytimes.com/subscription/cancel",
        "dark_pattern_rating": "High",
        "dark_pattern_notes": "Aggressive downgrade discounts presented before allowing cancellation."
    },
    "audible": {
        "name": "Audible Membership",
        "category": "Audio & Books",
        "canonical_name": "Audible Inc.",
        "icon": "headphones",
        "color": "#F39C12",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "Cancelling forfeits unspent membership credits unless consumed prior to cancellation.",
        "portal_url": "https://www.audible.com/account/overview",
        "dark_pattern_rating": "High",
        "dark_pattern_notes": "Warning dialogs about losing accumulated credits."
    },
    "dropbox": {
        "name": "Dropbox Plus",
        "category": "Cloud Storage",
        "canonical_name": "Dropbox Inc.",
        "icon": "hard-drive",
        "color": "#0061FF",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "Downgrade to Dropbox Basic. Files preserved but sync pauses if over 2GB quota.",
        "portal_url": "https://www.dropbox.com/account/plan",
        "dark_pattern_rating": "Low",
        "dark_pattern_notes": "Standard self-serve downgrade."
    },
    "github": {
        "name": "GitHub Copilot / Pro",
        "category": "Developer Tools",
        "canonical_name": "GitHub Inc.",
        "icon": "code",
        "color": "#24292E",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "Monthly or annual billing. Immediate self-serve cancellation under billing settings.",
        "portal_url": "https://github.com/settings/billing",
        "dark_pattern_rating": "Low",
        "dark_pattern_notes": "Clean developer-friendly cancellation."
    },
    "nordvpn": {
        "name": "NordVPN",
        "category": "Security & VPN",
        "canonical_name": "Nord Security",
        "icon": "shield",
        "color": "#4687FF",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "Auto-renewal toggle in billing settings. 30-day money-back guarantee for first purchase.",
        "portal_url": "https://my.nordaccount.com/billing/my-subscriptions/",
        "dark_pattern_rating": "Medium",
        "dark_pattern_notes": "Steep discount renewal banners, multiple confirmation prompts."
    },
    "coursera": {
        "name": "Coursera Plus",
        "category": "Education",
        "canonical_name": "Coursera Inc.",
        "icon": "award",
        "color": "#0056D2",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "Monthly or annual auto-charge. Certificates earned are retained permanently.",
        "portal_url": "https://www.coursera.org/account-profile/billing",
        "dark_pattern_rating": "Low",
        "dark_pattern_notes": "Standard online cancellation."
    },
    "duolingo": {
        "name": "Duolingo Super",
        "category": "Education",
        "canonical_name": "Duolingo Inc.",
        "icon": "smile",
        "color": "#58CC02",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "Billed via Web or App Store. Keeps streak and learning history intact.",
        "portal_url": "https://www.duolingo.com/settings/super",
        "dark_pattern_rating": "Low",
        "dark_pattern_notes": "Standard 2-screen flow."
    },
    "youtube": {
        "name": "YouTube Premium",
        "category": "Streaming Video & Music",
        "canonical_name": "Google LLC",
        "icon": "play-circle",
        "color": "#FF0000",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "Cancel anytime in Google Account Purchases & Memberships. Family plan recent price hike (+35%).",
        "portal_url": "https://www.youtube.com/paid_memberships",
        "dark_pattern_rating": "Medium",
        "dark_pattern_notes": "Prompt to pause instead of cancel for 1 to 6 months."
    },
    "hotstar": {
        "name": "Disney+ Hotstar / JioCinema",
        "category": "Streaming Video",
        "canonical_name": "Novi Digital Entertainment",
        "icon": "tv",
        "color": "#123F92",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "Annual or quarterly plan. Auto-renews unless turned off at least 48 hours prior to renewal date.",
        "portal_url": "https://www.hotstar.com/in/my-account",
        "dark_pattern_rating": "High",
        "dark_pattern_notes": "Disables active subscription auto-debit only after confirmation OTP."
    },
    "swiggy_one": {
        "name": "Swiggy One Membership",
        "category": "Food & Delivery",
        "canonical_name": "Bundl Technologies Pvt Ltd",
        "icon": "shopping-bag",
        "color": "#FC8019",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "3-month or annual auto-charge via UPI auto-mandate / credit card recurring.",
        "portal_url": "https://www.swiggy.com/my-account",
        "dark_pattern_rating": "High",
        "dark_pattern_notes": "Hidden in deep settings; often forgotten until surprise charge hits."
    },
    "zomato_gold": {
        "name": "Zomato Gold",
        "category": "Food & Delivery",
        "canonical_name": "Zomato Limited",
        "icon": "utensils",
        "color": "#CB202D",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "Recurring billing via card or UPI mandate. Free delivery benefits terminate on billing date.",
        "portal_url": "https://www.zomato.com",
        "dark_pattern_rating": "Medium",
        "dark_pattern_notes": "Promotional renewal pricing with countdown timers."
    },
    "cult_fit": {
        "name": "Cult.fit / Curefit Pass",
        "category": "Health & Fitness",
        "canonical_name": "Curefoods India Pvt Ltd",
        "icon": "activity",
        "color": "#FF3278",
        "cancellation_method": "agent_assisted_negotiation",
        "tos_summary": "Auto-debit recurring ₹1,999/mo. High inactivity vampire leak when gym attendance drops to 0.",
        "portal_url": "https://www.cult.fit",
        "dark_pattern_rating": "Extreme",
        "dark_pattern_notes": "Offers extension/pause instead of cancellation; requires multi-step support ticket."
    },
    "google_one": {
        "name": "Google One Storage (100GB/2TB)",
        "category": "Cloud Storage",
        "canonical_name": "Google LLC",
        "icon": "cloud",
        "color": "#4285F4",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "Storage quota decreases to 15GB upon cycle end. Photos and Gmail preserved but receiving emails may bounce if over quota.",
        "portal_url": "https://one.google.com/settings",
        "dark_pattern_rating": "Low",
        "dark_pattern_notes": "Warning prompt regarding Gmail space over-quota."
    },
    "apple_sub": {
        "name": "Apple Services & iCloud+",
        "category": "Cloud & Services",
        "canonical_name": "Apple Inc.",
        "icon": "smartphone",
        "color": "#A2AAAD",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "Managed via Apple ID Subscriptions. Cancellation halts at next billing date.",
        "portal_url": "https://support.apple.com/billing",
        "dark_pattern_rating": "Low",
        "dark_pattern_notes": "Requires device settings or iTunes billing access."
    },
    "canva": {
        "name": "Canva Pro",
        "category": "Design & Productivity",
        "canonical_name": "Canva Pty Ltd",
        "icon": "image",
        "color": "#00C4CC",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "Recent 2026 price revision (+25%). Cancels at end of billing cycle.",
        "portal_url": "https://www.canva.com/settings/billing-and-teams",
        "dark_pattern_rating": "Medium",
        "dark_pattern_notes": "Retention discounts offered before confirmation."
    },
    "figma": {
        "name": "Figma Professional",
        "category": "Design & Productivity",
        "canonical_name": "Figma Inc.",
        "icon": "layout",
        "color": "#F24E1E",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "Team and editor seat billing. Unused editor seats continue recurring billing.",
        "portal_url": "https://www.figma.com/settings",
        "dark_pattern_rating": "Medium",
        "dark_pattern_notes": "Downgrade team to starter tier."
    },
    "linkedin": {
        "name": "LinkedIn Premium Career",
        "category": "Professional",
        "canonical_name": "LinkedIn Ireland",
        "icon": "briefcase",
        "color": "#0077B5",
        "cancellation_method": "agent_direct_web",
        "tos_summary": "High price point ($39.99/mo). Free trial automatically converts to full billing.",
        "portal_url": "https://www.linkedin.com/premium/cancel",
        "dark_pattern_rating": "High",
        "dark_pattern_notes": "Multi-page survey and immediate offer of 50% discount for 2 months."
    }
}

class PrivacyScrubber:
    """Strict banking data privacy scrubber: sanitizes PII before processing."""
    
    # Regex patterns for sensitive PII
    CC_PATTERN = re.compile(r'\b(?:\d{4}[ -]){3}\d{4}\b|\b\d{16}\b|\b\d{4}-\d{4}-\d{4}-\d{4}\b')
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    ROUTING_ACCT_PATTERN = re.compile(r'\b(?:ACCT|ACC|A/C|RTN|ROUTING)[:#\s]*\d{6,12}\b', re.IGNORECASE)
    PHONE_PATTERN = re.compile(r'\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b')

    @classmethod
    def scrub_text(cls, text: str) -> Tuple[str, Dict[str, int]]:
        """Masks sensitive PII tokens and reports sanitization counts."""
        metrics = {"cc_masked": 0, "ssn_masked": 0, "emails_masked": 0, "acct_masked": 0, "phone_masked": 0}
        
        def mask_cc(match):
            metrics["cc_masked"] += 1
            raw = match.group(0).replace('-', '').replace(' ', '')
            return f"CARD-XXXX-XXXX-XXXX-{raw[-4:]}"

        def mask_acct(match):
            metrics["acct_masked"] += 1
            return "ACCT-MASKED-XXXX"

        def mask_email(match):
            metrics["emails_masked"] += 1
            return "[REDACTED-EMAIL]"

        scrubbed = cls.CC_PATTERN.sub(mask_cc, text)
        scrubbed = cls.SSN_PATTERN.sub(lambda m: (metrics.update(ssn_masked=metrics['ssn_masked']+1) or "[REDACTED-SSN]"), scrubbed)
        scrubbed = cls.ROUTING_ACCT_PATTERN.sub(mask_acct, scrubbed)
        scrubbed = cls.EMAIL_PATTERN.sub(mask_email, scrubbed)
        scrubbed = cls.PHONE_PATTERN.sub(lambda m: (metrics.update(phone_masked=metrics['phone_masked']+1) or "[REDACTED-PHONE]"), scrubbed)
        
        return scrubbed, metrics


class TransactionParser:
    """Parses raw statement strings or CSV records into structured transaction objects."""

    @staticmethod
    def parse_line(line: str) -> Dict[str, Any]:
        """Tries to extract Date, Description, Amount, and Transaction Type."""
        line = line.strip()
        if not line or line.startswith('#') or line.lower().startswith('date,'):
            return None
        
        # Support CSV: Date,Description,Amount or Date,Description,Debit,Credit
        parts = [p.strip(' "\'') for p in line.split(',')]
        if len(parts) >= 3:
            raw_date = parts[0]
            raw_desc = parts[1]
            raw_amt = parts[2]
            
            # Parse Date
            dt = None
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
                try:
                    dt = datetime.strptime(raw_date, fmt)
                    break
                except ValueError:
                    continue
            
            if not dt:
                return None
            
            # Parse Amount
            amt_clean = re.sub(r'[^\d.-]', '', raw_amt)
            try:
                amt = abs(float(amt_clean))
            except ValueError:
                return None
            
            return {
                "date": dt.strftime("%Y-%m-%d"),
                "timestamp": dt.timestamp(),
                "datetime": dt,
                "raw_description": raw_desc,
                "amount": amt
            }
        
        # Support unstructured text lines e.g.: "2026-09-15 NETFLIX.COM* 1234 LOS GATOS CA $15.49"
        date_match = re.search(r'\b(20\d\d[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]20\d\d)\b', line)
        amt_match = re.search(r'\$?([0-9]+\.[0-9]{2})\b', line)
        
        if date_match and amt_match:
            raw_date = date_match.group(1)
            raw_amt = amt_match.group(1)
            dt = None
            for sep in ('-', '/'):
                for fmt in (f"%Y{sep}%m{sep}%d", f"%m{sep}%d{sep}%Y", f"%d{sep}%m{sep}%Y"):
                    try:
                        dt = datetime.strptime(raw_date, fmt)
                        break
                    except ValueError:
                        continue
                if dt: break
            
            if dt:
                desc = line.replace(raw_date, '').replace(raw_amt, '').replace('$', '').strip(' ,;-')
                return {
                    "date": dt.strftime("%Y-%m-%d"),
                    "timestamp": dt.timestamp(),
                    "datetime": dt,
                    "raw_description": desc,
                    "amount": float(raw_amt)
                }
        
        return None


class PatternRecognitionEngine:
    """Core pattern recognition model that detects recurring charges, intervals, and vampire threats."""

    @classmethod
    def normalize_merchant(cls, raw_desc: str) -> Dict[str, Any]:
        """Maps messy transaction descriptions to canonical merchant entities."""
        desc_upper = raw_desc.upper()
        
        # Check against predefined catalog keywords
        matches = [
            ("netflix", ["NETFLIX", "NFLX"]),
            ("spotify", ["SPOTIFY"]),
            ("adobe", ["ADOBE", "CREATIVE CLOUD", "PHOTOPHY"]),
            ("amazon_prime", ["PRIME VIDEO", "AMAZON PRIME", "AMZN PRIME", "AMAZONPRIME"]),
            ("gym_fit", ["PLANET FIT", "EQUINOX", "CRUNCH GYM", "ANYTIME FIT", "GYM MEMBERSHIP", "GOLD'S GYM"]),
            ("openai", ["OPENAI", "CHATGPT", "OPENAI *CHATGPT"]),
            ("aws", ["AWS.AMAZON", "AMAZON WEB SERVICES", "AWS EMEA", "AWS CLOUD"]),
            ("nytimes", ["NYTIMES", "NEW YORK TIMES", "NYT DIGITAL"]),
            ("audible", ["AUDIBLE", "AUDIBLE.COM", "AMZN AUDIBLE"]),
            ("dropbox", ["DROPBOX"]),
            ("github", ["GITHUB"]),
            ("nordvpn", ["NORDVPN", "NORD VPN"]),
            ("coursera", ["COURSERA"]),
            ("duolingo", ["DUOLINGO"]),
            ("youtube", ["YOUTUBE", "GOOGLE *YOUTUBE", "YT PREMIUM", "YOUTUBEPREMIUM"]),
            ("hotstar", ["HOTSTAR", "JIOCINEMA", "JIO CINEMA", "DISNEY HOTSTAR", "DISNEY+"]),
            ("swiggy_one", ["SWIGGY", "SWIGGY ONE", "BUNDL TECH"]),
            ("zomato_gold", ["ZOMATO", "ZOMATO GOLD"]),
            ("cult_fit", ["CULT.FIT", "CULTFIT", "CUREFIT", "CURE.FIT"]),
            ("google_one", ["GOOGLE ONE", "GOOGLE *STORAGE", "GSUITE", "GOOGLE WORKSPACE"]),
            ("apple_sub", ["APPLE.COM/BILL", "APPLE SERVICES", "ICLOUD", "ITUNES.COM"]),
            ("canva", ["CANVA", "CANVA PRO"]),
            ("figma", ["FIGMA"]),
            ("linkedin", ["LINKEDIN", "LINKEDIN PREM"])
        ]
        
        for key, aliases in matches:
            for alias in aliases:
                if alias in desc_upper:
                    info = MERCHANT_CATALOG[key].copy()
                    info["key"] = key
                    return info
        
        # Fallback for unrecognized merchant: extract clean title using regex
        cleaned = re.sub(r'[*#\d]+|\b(INC|LLC|CORP|COM|LTD|PAYMENTS|BILLING|RECURRING|SUBSCRIPTION|CHECKOUT|US|CA|DIRECT DEBIT)\b', '', desc_upper)
        cleaned = re.sub(r'[^A-Z\s]', '', cleaned).strip()
        cleaned_words = [w for w in cleaned.split() if len(w) > 2]
        title = " ".join(cleaned_words[:3]).title() if cleaned_words else "Recurring Provider"
        
        return {
            "key": re.sub(r'[^a-z0-9]', '_', title.lower()),
            "name": title,
            "category": "General Subscription",
            "canonical_name": title,
            "icon": "credit-card",
            "color": "#64748B",
            "cancellation_method": "agent_assisted_negotiation",
            "tos_summary": "Standard merchant cancellation. Contact customer support or check account billing settings.",
            "portal_url": "",
            "dark_pattern_rating": "Medium",
            "dark_pattern_notes": "Generic provider pattern."
        }

    @classmethod
    def analyze_transactions(cls, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Groups transactions by normalized merchant, computes recurrence intervals,
        flags vampire risks (price creep, free trial trap, zombie inactivity),
        and projects renewal schedules.
        """
        # Group by merchant
        merchant_groups: Dict[str, List[Dict[str, Any]]] = {}
        for tx in transactions:
            m_info = cls.normalize_merchant(tx["raw_description"])
            m_key = m_info["key"]
            if m_key not in merchant_groups:
                merchant_groups[m_key] = {
                    "merchant_info": m_info,
                    "transactions": []
                }
            tx_record = tx.copy()
            merchant_groups[m_key]["transactions"].append(tx_record)

        detected_subscriptions = []
        total_monthly_drain = 0.0
        vampire_costs_eliminated = 0.0
        vampire_threat_count = 0

        # Current reference time for scheduling next renewals
        now = datetime.now()

        for m_key, group in merchant_groups.items():
            txs = group["transactions"]
            # Sort chronologically
            txs.sort(key=lambda x: x["datetime"])
            
            m_info = group["merchant_info"]
            count = len(txs)
            
            # Require at least 2 charges for cadence analysis (or single trial charge of 0.00 followed by notice)
            if count < 2:
                # If single charge with explicit trial keywords or high recurring likelihood
                if count == 1 and any(k in txs[0]["raw_description"].upper() for k in ["TRIAL", "SUB", "MEMBERSHIP", "RECURRING"]):
                    single_tx = txs[0]
                    detected_subscriptions.append({
                        "id": f"sub_{m_key}_{int(single_tx['timestamp'])}",
                        "merchant_key": m_key,
                        "merchant_name": m_info["name"],
                        "category": m_info["category"],
                        "icon": m_info["icon"],
                        "color": m_info["color"],
                        "cadence": "Monthly (Estimated)",
                        "billing_cycle_type": "Fixed",
                        "current_amount": single_tx["amount"],
                        "monthly_equivalent": single_tx["amount"],
                        "annual_projected": single_tx["amount"] * 12,
                        "transaction_count": 1,
                        "first_seen": single_tx["date"],
                        "last_billed": single_tx["date"],
                        "next_renewal": (single_tx["datetime"] + timedelta(days=30)).strftime("%Y-%m-%d"),
                        "days_until_renewal": max(1, ((single_tx["datetime"] + timedelta(days=30)) - now).days),
                        "confidence_score": 68,
                        "vampire_threat_score": 75,
                        "vampire_flags": ["New / Unconfirmed Recurring Charge"],
                        "price_creep_pct": 0.0,
                        "price_history": [single_tx["amount"]],
                        "status": "Active",
                        "tos_summary": m_info["tos_summary"],
                        "cancellation_method": m_info["cancellation_method"],
                        "portal_url": m_info["portal_url"],
                        "dark_pattern_rating": m_info["dark_pattern_rating"],
                        "dark_pattern_notes": m_info["dark_pattern_notes"]
                    })
                continue

            # Calculate inter-arrival intervals in days
            intervals = []
            for i in range(1, count):
                delta_days = (txs[i]["datetime"] - txs[i-1]["datetime"]).days
                intervals.append(delta_days)

            avg_interval = sum(intervals) / len(intervals) if intervals else 30
            amounts = [t["amount"] for t in txs]
            latest_amount = amounts[-1]
            first_amount = amounts[0]
            
            # Amount variance
            amt_variance = sum((a - sum(amounts)/len(amounts))**2 for a in amounts) / len(amounts)
            amt_std = math.sqrt(amt_variance)
            is_variable = amt_std > 2.0 and (m_key in ["aws", "azure", "gcp"] or "CLOUD" in m_info["name"].upper() or "UTILITY" in m_info["name"].upper())

            # Detect Cadence
            if 5 <= avg_interval <= 9:
                cadence = "Weekly"
                monthly_mult = 4.33
                predicted_delta = 7
            elif 12 <= avg_interval <= 16:
                cadence = "Bi-Weekly"
                monthly_mult = 2.16
                predicted_delta = 14
            elif 25 <= avg_interval <= 35:
                cadence = "Monthly"
                monthly_mult = 1.0
                predicted_delta = 30
            elif 80 <= avg_interval <= 100:
                cadence = "Quarterly"
                monthly_mult = 1/3.0
                predicted_delta = 90
            elif 340 <= avg_interval <= 380:
                cadence = "Annual"
                monthly_mult = 1/12.0
                predicted_delta = 365
            else:
                cadence = f"Irregular (~{int(avg_interval)}d)"
                monthly_mult = 30.0 / max(avg_interval, 1)
                predicted_delta = max(int(avg_interval), 30)

            monthly_cost = round(latest_amount * monthly_mult, 2)
            annual_cost = round(monthly_cost * 12, 2)
            total_monthly_drain += monthly_cost

            # Compute Next Renewal Date
            last_date = txs[-1]["datetime"]
            next_renewal_dt = last_date + timedelta(days=predicted_delta)
            while next_renewal_dt < now:
                next_renewal_dt += timedelta(days=predicted_delta)
            days_left = max(0, (next_renewal_dt - now).days)

            # Vampire Cost Analysis & Threat Scoring (0 - 100)
            vampire_flags = []
            threat_score = 15 # baseline

            # 1. Price Creep Detection (silent hike)
            price_creep_pct = 0.0
            if first_amount > 0 and latest_amount > first_amount:
                price_creep_pct = round(((latest_amount - first_amount) / first_amount) * 100, 1)
                if price_creep_pct >= 10:
                    vampire_flags.append(f"Silent Price Creep (+{price_creep_pct}% from initial ${first_amount:.2f})")
                    threat_score += 35

            # 2. Free Trial Expiration Trap (0 or ~1 dollar leading to large recurring)
            if any(a <= 1.0 for a in amounts[:-1]) and latest_amount > 10.0:
                vampire_flags.append(f"Free Trial Trap Converted to Full Billing (${latest_amount:.2f})")
                threat_score += 40

            # 3. Zombie Inactivity / Dark Pattern traps (Known sticky merchants)
            if m_key in ["gym_fit", "audible", "adobe", "nytimes", "cult_fit", "swiggy_one", "hotstar", "linkedin"]:
                if m_key in ["gym_fit", "cult_fit"]:
                    vampire_flags.append("High Inactivity Leak (Gym Pass Auto-Debit with 0 attendance)")
                    threat_score += 35
                elif m_key == "adobe":
                    vampire_flags.append("Early Termination Fee Dark Pattern Risk (50% remaining balance)")
                    threat_score += 30
                elif m_key == "audible":
                    vampire_flags.append("Unused Credits Drain (Recurring charge despite unspent balances)")
                    threat_score += 25
                elif m_key == "nytimes":
                    vampire_flags.append("Introductory Promo Expired (Price reset to standard tier)")
                    threat_score += 30
                elif m_key == "swiggy_one":
                    vampire_flags.append("Hidden Auto-Debit Renewal (Forgotten delivery perks pass)")
                    threat_score += 25
                elif m_key == "linkedin":
                    vampire_flags.append("High-Cost Tier ($39.99/mo renewal after 30-day free trial)")
                    threat_score += 35
                elif m_key == "hotstar":
                    vampire_flags.append("Annual Auto-Debit Lock (48-hr advance cancellation restriction)")
                    threat_score += 25

            # 4. High Frequency / Redundant category check
            if m_info["category"] == "Streaming Video" and m_key in ["netflix", "amazon_prime"]:
                threat_score += 15

            # 5. Imminent Renewal Alert (< 4 days)
            if days_left <= 3:
                vampire_flags.append(f"Imminent Auto-Renewal in {days_left} days!")
                threat_score += 20

            threat_score = min(99, threat_score)
            if threat_score >= 50:
                vampire_threat_count += 1

            # Recurrence confidence calculation
            confidence = 70
            if len(intervals) >= 2:
                interval_var = sum((inv - avg_interval)**2 for inv in intervals) / len(intervals)
                if interval_var < 9:
                    confidence = 96
                elif interval_var < 36:
                    confidence = 88
                else:
                    confidence = 78
            else:
                confidence = 82

            sub_item = {
                "id": f"sub_{m_key}_{int(txs[-1]['timestamp'])}",
                "merchant_key": m_key,
                "merchant_name": m_info["name"],
                "category": m_info["category"],
                "icon": m_info["icon"],
                "color": m_info["color"],
                "cadence": cadence,
                "billing_cycle_type": "Variable Usage" if is_variable else "Fixed Recurring",
                "current_amount": latest_amount,
                "monthly_equivalent": monthly_cost,
                "annual_projected": annual_cost,
                "transaction_count": count,
                "first_seen": txs[0]["date"],
                "last_billed": txs[-1]["date"],
                "next_renewal": next_renewal_dt.strftime("%Y-%m-%d"),
                "days_until_renewal": days_left,
                "confidence_score": confidence,
                "vampire_threat_score": threat_score,
                "vampire_flags": vampire_flags,
                "price_creep_pct": price_creep_pct,
                "price_history": amounts,
                "status": "Active",
                "tos_summary": m_info["tos_summary"],
                "cancellation_method": m_info["cancellation_method"],
                "portal_url": m_info["portal_url"],
                "dark_pattern_rating": m_info["dark_pattern_rating"],
                "dark_pattern_notes": m_info["dark_pattern_notes"]
            }
            detected_subscriptions.append(sub_item)

        # Sort subscriptions: highest vampire threat first
        detected_subscriptions.sort(key=lambda s: s["vampire_threat_score"], reverse=True)

        return {
            "subscriptions": detected_subscriptions,
            "metrics": {
                "active_subscriptions_count": len(detected_subscriptions),
                "total_monthly_drain": round(total_monthly_drain, 2),
                "projected_annual_drain": round(total_monthly_drain * 12, 2),
                "vampire_threats_detected": vampire_threat_count,
                "high_risk_monthly_burn": round(sum(s["monthly_equivalent"] for s in detected_subscriptions if s["vampire_threat_score"] >= 50), 2)
            }
        }

# Hashnode Canonical Syndicator & SEO Authority Booster

Autonomous content syndicator for **[aviperera.com](https://aviperera.com)** that cross-publishes research dossiers and essays to Hashnode via their official GraphQL API.

Every article published through this engine embeds an official **`originalArticleURL` pointing directly back to the origin publication on `aviperera.com`**. This instructs Google and Hashnode to channel **100% of the SEO backlink equity directly to your personal domain**, establishing authoritative canonical backlinks while tapping into Hashnode’s developer and technical audience (DA 85+).

---

## 🚀 Key Capabilities

1. **Official GraphQL API**:
   - Uses Hashnode’s permanent, public API endpoint (`https://gql.hashnode.com`).
   - Hashnode explicitly encourages cross-posting and supports CI/CD automation without account risk.
2. **Native Canonical Attribution**:
   - Explicitly sets `originalArticleURL: https://aviperera.com/<post-slug>/` on every article.
   - Preserves complete SEO link equity and prevents duplicate content penalties.
3. **HTML to Markdown Pipeline**:
   - Parses WordPress content into clean GitHub-flavored Markdown.
   - Formats headings, code blocks, lists, quotes, and links natively.
   - Automatically appends a canonical attribution citation at the bottom of each article.
4. **Auto-Detection of Publication**:
   - Automatically detects your primary publication ID from your account if not explicitly specified.
5. **Deduplication & Cadence**:
   - Tracks syndicated articles in `state/hashnode_history.json`.
   - Paces publication to 1 article per scheduled run to ensure optimal reach and reader discovery.

---

## 🛠️ Configuration & Secrets

Add the following secret in your repository:  
**Settings** ➔ **Secrets and variables** ➔ **Actions** ➔ **New repository secret**:

| Secret Name | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| `HASHNODE_TOKEN` | **Yes** | — | Personal Access Token from Hashnode Account Settings. |
| `HASHNODE_PUBLICATION_ID` | *Optional* | *Auto-detected* | Your blog publication ID (auto-resolved from your account if omitted). |

---

## 📌 How to Obtain Your Hashnode Personal Access Token

1. Log in to your account at [hashnode.com](https://hashnode.com).
2. Click your profile avatar ➔ **Account Settings** (or go to `hashnode.com/settings/developer`).
3. Scroll down to **Developer** ➔ **Personal Access Tokens**.
4. Click **Generate New Token**, enter a name (e.g. `Avi Syndicator`), and click **Generate**.
5. Copy the generated token and save it as `HASHNODE_TOKEN` in your repository secrets.

---

## 🧪 Local Testing

```bash
python -m unittest discover tests
python hashnode_engine.py --dry-run
```

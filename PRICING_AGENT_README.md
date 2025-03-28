# Pricing Agent

The Pricing Agent is a comprehensive SaaS pricing expert that combines insights from both community knowledge and expert reports to provide complete answers to pricing questions.

## Features

- Runs both the Community Agent and Reports Agent in parallel
- Combines insights from community forums and expert reports
- Provides a single, coherent response with citations from both sources
- Highlights areas of agreement and complementary information
- Includes all relevant citations and references

## How It Works

1. When a user asks a pricing question, the agent runs both the Community Agent and Reports Agent in parallel
2. The Community Agent searches through Discourse forums for relevant community knowledge
3. The Reports Agent searches through expert reports and documents
4. The Pricing Agent combines the results into a single, coherent response
5. All citations and references from both sources are included in the response

## Usage

To run the Pricing Agent interactively:

```bash
./run_pricing_agent.sh
```

Or manually:

```bash
python3 ./test_pricing_agent.py
```

## Example

```
Enter your pricing question: What are the best practices for SaaS pricing models?

Pricing Agent: Gathering information from community and reports...
Pricing Agent: Found relevant information from both sources.
Pricing Agent: Based on insights from both community discussions and expert reports, here are the best practices for SaaS pricing models:

# Core SaaS Pricing Models

1. **Tiered Pricing**: Offering different feature sets at different price points
   - Community users report this is the most common model, with 3-4 tiers being optimal
   - Expert reports confirm this approach works well for most SaaS businesses

2. **Usage-Based Pricing**: Charging based on consumption metrics
   - Reports indicate this model aligns well with customer value perception
   - Community experience shows it works particularly well for infrastructure and API services

3. **Per-User Pricing**: Charging based on number of users
   - Both sources agree this model is simple to understand but may discourage adoption
   - Reports suggest combining with feature tiers for better results

4. **Freemium**: Offering a free tier with limited functionality
   - Community discussions highlight this as effective for viral growth
   - Expert analysis shows conversion rates typically range from 2-5%

# Best Practices (Consensus from Both Sources)

1. **Value-Based Pricing**: Price according to the value delivered, not costs
   - Reports emphasize this as the #1 principle for SaaS pricing
   - Community examples show companies achieving 20-30% higher revenue with this approach

2. **Regular Testing and Optimization**: 
   - Community members report 10-15% revenue increases from regular price testing
   - Expert documents recommend quarterly pricing reviews

3. **Clear Value Communication**:
   - Both sources emphasize transparent pricing pages with clear value propositions
   - Reports show that effective value communication can increase conversion by up to 30%

4. **Grandfathering Existing Customers**:
   - Community consensus strongly favors this approach when raising prices
   - Reports confirm this preserves customer goodwill while allowing price optimization

# Additional Insights

- **From Community**: Real-world implementation challenges often involve sales team alignment and customer objection handling
- **From Reports**: Psychological pricing tactics (e.g., charm pricing at $99 instead of $100) can increase conversion rates by 5-10%

References:
[1] [Community] SaaS Pricing Models Discussion - https://community.pricingsaas.com/t/123
[2] [Community] Value-Based Pricing Success Stories - https://community.pricingsaas.com/t/456
[3] [Report] SaaS Pricing Optimization Guide - doc-789
[4] [Report] Freemium Conversion Benchmarks - doc-012
```

## Development

The Pricing Agent is built using the OpenAI Agents framework and combines two specialized agents:

1. **Community Agent**: Searches through Discourse forums for community knowledge
2. **Reports Agent**: Searches through expert reports and documents

The agent uses asyncio to run both agents in parallel and then combines their results into a single response.

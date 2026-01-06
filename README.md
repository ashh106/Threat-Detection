Behavioral Anomaly Detection for Insider Threat Detection
A production-ready, explainable behavioral analytics system for detecting insider threats and data leakage using statistical methods and unsupervised learning.

🎯 Project Overview
This system learns "normal" user behavior patterns and detects statistical anomalies that may indicate insider threats, without requiring labeled training data.

Key Features
Unsupervised Learning: No labeled data needed for training
Multi-Baseline Analysis: Compares behavior across personal, peer, and temporal dimensions
Explainable by Design: Every alert includes clear explanations (z-scores, percentiles, drift metrics)
Production-Ready: Supports both batch and real-time inference
Privacy-Aware: Configurable anonymization and data retention policies
Microsoft Ecosystem: Designed for integration with Azure Sentinel, Defender for Endpoint
📊 How It Works
Three-Pillar Behavioral Analysis
Personal Baseline: How does this user's behavior compare to their own history?
Example: Alice normally sends 5 emails/day, suddenly sends 100
Peer Baseline: How does this user compare to colleagues in the same role?
Example: Alice (engineer) sends 100 emails, but sales team averages 150
Temporal Baseline: Is this behavior unusual for this time of day/week?
Example: Alice logs in at 3 AM on Sunday
Mathematical Foundation
For each feature (e.g., email count), we model the distribution:

Gaussian Distribution (for normal features):

z-score = (observed_value - mean) / std_deviation
|z| > 3 indicates 99.7% of values are below this (anomaly)
Percentile Distribution (for non-Gaussian features):

percentile_rank = rank(value) / total_values * 100
percentile > 95 indicates top 5% (anomaly)
Final Score Fusion:

anomaly_score = w1·personal_score + w2·peer_score + w3·temporal_score
🚀 Quick Start Guide
Prerequisites
Python 3.8+
4GB+ RAM
CERT Insider Threat Dataset
Installation
Clone/Download Project
bash
cd insider_threat_detection
Install Dependencies
bash
pip install -r requirements.txt
Download CERT Dataset
Go to Kaggle CERT Dataset
Download and extract to data/raw/
Verify Setup
bash
python -c "import pandas, numpy, scipy, sklearn; print('✓ All dependencies installed')"
Project Structure Setup
bash
# Create directory structure
mkdir -p data/{raw,processed,features}
mkdir -p models/distributions
mkdir -p logs
mkdir -p results/dashboard
mkdir -p notebooks
📖 Step-by-Step Usage
Step 1: Train the Model (Build Baselines)
bash
python train.py --config config.yaml
What this does:

Loads raw CERT CSV files (logon, email, device, file, http)
Engineers behavioral features (email counts, logon frequency, etc.)
Builds statistical distributions for each user-feature pair
Creates peer group baselines by role
Creates temporal baselines by hour/day
Saves trained models to models/distributions/
Expected Output:

[STEP 1/5] Loading raw CERT data...
  Loaded 18,000,000 logon records
  Loaded 750,000 email records
  ...

[STEP 2/5] Engineering behavioral features...
  Created unified matrix: 450,000 records × 25 features

[STEP 3/5] Splitting training and validation sets...
  Training set: 315,000 observations
  Validation set: 135,000 observations

[STEP 4/5] Building behavioral distributions...
  ✓ Personal distributions: 950 users
  ✓ Peer distributions: 45 roles
  ✓ Temporal distributions: 24 time buckets

[STEP 5/5] Saving trained models...
  ✓ Models saved to: models/distributions/baseline_distributions.pkl

VALIDATION
  Severity distribution:
    NORMAL: 127,350 (94.3%)
    LOW: 4,050 (3.0%)
    MEDIUM: 2,025 (1.5%)
    HIGH: 1,350 (1.0%)
    CRITICAL: 225 (0.2%)

TRAINING COMPLETE
Time Required: 10-30 minutes depending on dataset size

Step 2: Run Inference (Detect Anomalies)
Batch Inference (score a full dataset):

bash
python inference.py \
  --input data/features/behavioral_features.csv \
  --output results/ \
  --model models/distributions/baseline_distributions.pkl
Expected Output:

[STEP 1/4] Loading trained models...
  ✓ Loaded 950 personal baselines
  ✓ Loaded 45 peer baselines

[STEP 2/4] Loading input data...
  Loaded 10,000 observations

[STEP 3/4] Scoring observations...
  Scored 10,000 observations

Anomaly Detection Results:
  NORMAL: 9,450 (94.5%)
  LOW: 300 (3.0%)
  MEDIUM: 150 (1.5%)
  HIGH: 75 (0.75%)
  CRITICAL: 25 (0.25%)

Top 10 Anomalies:
  USER042 on 2024-03-15 - Score: 0.927 (CRITICAL)
    → email_sent_count: 150 is significantly higher than user's normal (15.3 std deviations)

[STEP 4/4] Saving results...
  ✓ Detailed results: results/anomaly_scores.csv
  ✓ High-priority alerts: results/high_priority_alerts.csv
  ✓ Dashboard created: results/dashboard/report.html

INFERENCE COMPLETE
Real-Time Inference (stream processing):

bash
python inference.py --realtime --stream-source kafka://events
Step 3: Visualize Results
bash
# View HTML dashboard
open results/dashboard/report.html  # macOS
start results/dashboard/report.html # Windows
xdg-open results/dashboard/report.html # Linux
Visualizations Included:

Anomaly timeline: Score trends over time
Severity distribution: Breakdown of alert levels
Feature importance: Which behaviors trigger most alerts
User comparisons: Individual vs peer behavior
Behavioral heatmaps: Activity patterns by hour/day
🔬 Understanding the Output
Anomaly Score Interpretation
Score Range	Severity	Meaning	Action
0.0 - 0.3	NORMAL	Typical behavior	No action
0.3 - 0.5	LOW	Slightly unusual	Log for pattern tracking
0.5 - 0.7	MEDIUM	Moderately anomalous	Review if persistent
0.7 - 0.9	HIGH	Highly suspicious	Investigate
0.9 - 1.0	CRITICAL	Extremely anomalous	Immediate investigation
Example Alert Explanation
USER: USER042
DATE: 2024-03-15
ANOMALY SCORE: 0.927 (CRITICAL)

FLAGGED BEHAVIORS:
1. email_sent_count: 150 (normally 10±3)
   - Personal z-score: 46.7 (!!!)
   - Peer z-score: 12.3
   - Temporal percentile: 99.8th

2. unique_recipients_count: 120 (normally 8±2)
   - Personal z-score: 56.0 (!!!)
   - Peer z-score: 15.4

3. cloud_storage_access_count: 25 (normally 0±0)
   - Personal z-score: N/A (new behavior)
   - Temporal percentile: 98.5th

EXPLANATION:
Email volume is significantly higher than user's normal (46.7 std deviations);
Unusual for this time of day (99.8th percentile);
First time accessing cloud storage
This explanation tells the analyst:

What changed: Email volume spiked
How much: 46.7 standard deviations (extremely unusual)
Compared to whom: Both personal history and peers
When: Unusual for this time of day
Context: New behavior (cloud storage access)
🎓 Deep Dive: How the Model Works
Feature Engineering
Raw logs are transformed into behavioral features:

Input (raw log):

2024-03-15 09:15:30, USER042, Logon, PC-123
2024-03-15 09:16:45, USER042, Email Send, recipient@example.com
2024-03-15 09:17:22, USER042, Email Send, recipient2@example.com
...
Output (aggregated features per user-day):

user: USER042
date: 2024-03-15
logon_count: 5
email_sent_count: 150
after_hours_logon_count: 0
usb_connect_count: 0
cloud_storage_access_count: 25
...
Distribution Building (Training)
For each user and each feature, we fit a statistical distribution:

python
# Example: Email count distribution for USER042
observations = [10, 12, 9, 11, 10, 13, 9, 10, ...]  # 30 days of history

# Fit Gaussian distribution
mean = 10.3
std = 1.4

# Store parameters
personal_baseline[USER042][email_count] = {
    'mean': 10.3,
    'std': 1.4,
    'percentiles': {5: 8, 50: 10, 95: 13, 99: 15}
}
Anomaly Scoring (Inference)
When new observation arrives:

python
# New observation
new_value = 150

# Score against personal baseline
z_score = (150 - 10.3) / 1.4 = 99.8  # EXTREMELY HIGH!

# Score against peer baseline (engineers average 30±10)
peer_z = (150 - 30) / 10 = 12.0  # Still very high

# Score against temporal baseline (9 AM normally has low activity)
temporal_percentile = 99.8  # Top 0.2% of activity at this hour

# Fuse scores
anomaly_score = 0.5 * normalize(99.8) + 0.3 * normalize(12.0) + 0.2 * (99.8/100)
              = 0.5 * 0.99 + 0.3 * 0.92 + 0.2 * 0.998
              = 0.972 (CRITICAL)
🛠️ Advanced Configuration
Config File (config.yaml)
yaml
# Feature Engineering
features:
  aggregation_window: "1D"  # Change to "1H" for hourly features
  
  working_hours:
    start: 6   # 6 AM
    end: 18    # 6 PM

# Distribution Building
distributions:
  training_window_days: 30
  min_observations: 10  # Minimum samples to build distribution
  
# Anomaly Scoring
anomaly_detection:
  z_score_threshold: 3.0
  percentile_threshold: 95
  
  fusion_weights:
    personal: 0.5   # Weight for personal baseline
    peer: 0.3       # Weight for peer baseline
    temporal: 0.2   # Weight for temporal baseline
  
  alert_threshold: 0.7  # Final score threshold for alerts
Custom Feature Engineering
Add your own features by modifying feature_engineering.py:

python
def engineer_custom_features(self, data: pd.DataFrame) -> pd.DataFrame:
    """Engineer custom features."""
    features = {}
    
    # Example: VPN usage patterns
    features['vpn_connection_count'] = data.groupby(['user', 'date_only']).size()
    
    # Example: Data exfiltration risk
    features['large_file_transfers'] = data[data['size'] > 100MB].groupby(['user', 'date_only']).size()
    
    return pd.DataFrame(features)
🔒 Privacy & Compliance
Privacy Features
User Anonymization: Enable in config
yaml
privacy:
  anonymize_users: true  # Replace user IDs with hashed values
Data Retention: Automatic cleanup
yaml
privacy:
  retention_days: 180  # Delete behavioral data after 6 months
Sensitive Field Hashing:
yaml
privacy:
  hash_pii: true  # Hash email addresses, URLs
GDPR Compliance
User data is aggregated and anonymized
No PII stored in behavioral baselines
Right to deletion: Remove user from all distributions
Data minimization: Only behavioral statistics stored
🚨 Production Deployment
Architecture
┌─────────────────┐
│  Event Sources  │  (Logs, SIEM, Sensors)
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Feature Engine  │  (Real-time aggregation)
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Anomaly Scorer  │  (Statistical comparison)
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Alert Engine   │  (Priority filtering)
└────────┬────────┘
         │
         v
┌─────────────────┐
│  SIEM / SOC     │  (Investigation)
└─────────────────┘
Integration with Microsoft Ecosystem
Azure Sentinel Integration:

python
# Send alerts to Azure Sentinel
from azure.monitor.query import LogsQueryClient

def send_to_sentinel(alert):
    client = LogsQueryClient(credential)
    client.query_workspace(
        workspace_id=WORKSPACE_ID,
        query=f"CustomLog_CL | where AnomalyScore > {alert['score']}"
    )
Microsoft Defender Integration:

python
# Enrich with Defender data
from microsoft.graph import GraphServiceClient

def get_device_risk(user):
    risk = graph_client.users.by_user_id(user).get().risk_level
    return risk
Performance Optimization
For Large Datasets:

python
# Use parallel processing
from joblib import Parallel, delayed

results = Parallel(n_jobs=-1)(
    delayed(score_observation)(obs) for obs in observations
)
For Real-Time:

python
# Use caching for distributions
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_user_distribution(user, feature):
    return distributions[user][feature]
📊 Evaluation & Tuning
Metrics to Monitor
False Positive Rate: Percentage of normal behavior flagged
Target: < 5% at HIGH/CRITICAL severity
Alert Fatigue: Alerts per day per analyst
Target: < 20 actionable alerts/day
Detection Rate: Known incidents caught
Validate against answer key in CERT dataset
Tuning Guide
Too many false positives?

Increase alert_threshold (0.7 → 0.8)
Increase z_score_threshold (3.0 → 3.5)
Increase min_observations (10 → 20)
Missing real threats?

Decrease alert_threshold (0.7 → 0.6)
Add more feature types
Increase fusion_weights for personal baseline
Performance issues?

Reduce aggregation_window granularity
Use sampling for distribution building
Implement feature selection
🐛 Troubleshooting
Common Issues
Issue: "No distribution for user X"

Solution: User has insufficient historical data (< min_observations)
Fix: Lower min_observations in config or collect more data
Issue: "All users showing as anomalous"

Solution: Distribution parameters are incorrect
Fix: Verify feature engineering step, check for data quality issues
Issue: "Training takes too long"

Solution: Large dataset
Fix: Use sampling, increase aggregation window, or use parallel processing
Debug Mode
bash
# Run with verbose logging
python train.py --config config.yaml --log-level DEBUG

# Check intermediate outputs
ls -lh data/features/
ls -lh models/distributions/
📚 Further Reading
Academic Papers
"Bridging the Gap: A Pragmatic Approach to Generating Insider Threat Data" (CERT)
"Anomaly Detection for Insider Threats Using Unsupervised Ensembles"
Related Technologies
UEBA (User and Entity Behavior Analytics)
Statistical Process Control
Time Series Anomaly Detection
Isolation Forest, One-Class SVM
🤝 Contributing
This is a hackathon project, but contributions are welcome:

Feature engineering improvements
New distribution types (e.g., Poisson for count data)
Integration connectors
Performance optimizations
📝 License
MIT License - See LICENSE file

🙏 Acknowledgments
CERT Division at Carnegie Mellon University for the dataset
Microsoft Security team for Azure Sentinel integration patterns
Open source community for foundational libraries
📞 Support
For questions or issues:

Open a GitHub issue
Review the troubleshooting section
Check logs in logs/ directory
Built for Microsoft Cybersecurity AI Hackathon 🎯


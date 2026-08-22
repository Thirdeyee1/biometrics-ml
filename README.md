#Continuous User Authentication Using Keyboard and Mouse Behavioral Biometrics with a Random Forest Classifier

This repository contains a machine learning-based behavioral biometrics system for user identification and continuous authentication using keyboard and mouse interaction patterns.

The project collects behavioral data from users through Python-based keyboard and mouse monitoring scripts, extracts relevant behavioral features, evaluates feature importance using Gini Mean Decrease in Impurity, and uses a Random Forest Classifier to distinguish between different users based on their interaction behavior.

Project Workflow

The system is divided into several stages:

Keyboard & Mouse Activity
          │
          ▼
    Data Collection
          │
          ▼
   Feature Extraction
          │
          ▼
   Gini Importance
          │
          ▼
  Feature Selection
          │
          ▼
  Train-Test Split
          │
          ▼
 Random Forest Classifier
          │
          ▼
 Model Validation
          │
          ▼
 Performance Evaluation
1. Behavioral Data Collection

Python scripts are used to collect keyboard and mouse interaction data while users interact with the computer.

The collected behavioral information includes mouse and keyboard interaction characteristics that can be used to distinguish between users.

The data collection process is performed in behavioral windows, allowing user activity to be represented as individual samples for machine learning.

The collected data are subsequently processed and prepared for feature extraction and model training.

2. Feature Extraction

The collected keyboard and mouse events are transformed into numerical behavioral features that describe how a user interacts with the computer.

Mouse Behavioral Features

The mouse-related features include characteristics such as:

Average mouse position
Mouse movement distance
Mouse speed
Mouse acceleration
Mouse click activity
Click-related timing characteristics
Keyboard Behavioral Features

Keyboard interaction is represented using timing and typing-related characteristics, including features such as:

Key press and release timing
Key hold duration
Key-to-key timing
Typing behavior
Pause characteristics
Key frequency statistics

These features provide a behavioral representation of each user that can be used by the machine learning model.

3. Feature Importance Using Gini Mean Decrease in Impurity

Before training the final model, feature importance is evaluated using a Random Forest-based Gini Mean Decrease in Impurity approach.

Gini importance measures how much each feature contributes to reducing impurity across the decision trees in the Random Forest.

The resulting feature importance ranking is used to identify the behavioral characteristics that contribute most to distinguishing between users.

Figure: Gini importance ranking of the selected keyboard and mouse behavioral features.

4. Train-Test Split

The dataset is divided into training and testing subsets using a 70:30 stratified train-test split.

70% — Training Set
30% — Testing Set

Stratification is applied to maintain the distribution of the different user classes across both subsets.

Figure: 70:30 stratified train-test split.

5. Random Forest Classification

The primary machine learning model used in this project is a Random Forest Classifier.

Random Forest is a supervised machine learning algorithm that combines multiple decision trees to perform classification.

In this project, the model learns patterns in keyboard and mouse behavioral features and uses these patterns to classify an interaction sample according to the corresponding user.

The Random Forest model is trained using the selected behavioral features and evaluated on previously unseen test data.

6. Model Validation

Model performance is evaluated using 5-Fold Stratified Cross-Validation in addition to the hold-out test set.

The validation process is used to assess how consistently the Random Forest model performs across different subsets of the dataset.

The project evaluates the model using metrics and visualizations including:

Accuracy
Cross-validation scores
Classification report
Confusion matrix
Feature importance
Validation analysis
7. Confusion Matrix

The confusion matrix provides a detailed view of the Random Forest classification results for the different user classes.

The diagonal values represent correctly classified samples, while the off-diagonal values represent samples that were incorrectly classified as another user.

Figure: Random Forest classification confusion matrix.

Results

The current Random Forest experiment achieved an accuracy of 62.85%, correctly classifying 1,267 out of 2,016 test samples.

The results indicate that keyboard and mouse behavioral characteristics contain distinguishable patterns that can be used for user classification.

However, the current results also demonstrate that additional data collection, feature engineering, and model optimization may be required to improve the reliability and generalization of the authentication system.

Project Components

The repository contains Python scripts covering the main stages of the experiment:

Keyboard and Mouse Data Collection — records user interaction behavior.
Data Processing and Feature Extraction — prepares behavioral data for machine learning.
Gini Importance Analysis — evaluates and ranks behavioral features.
Accuracy and Validation Analysis — evaluates model performance.
Random Forest Model — trains and evaluates the supervised classification model.
Research Objective

The primary objective of this project is to investigate whether keyboard and mouse behavioral biometrics can be used with supervised machine learning to distinguish between users continuously based on their interaction patterns.

Rather than relying only on traditional authentication at login, behavioral biometrics provides a potential approach for monitoring user behavior throughout a computer session.

This repository serves as a research prototype for exploring behavioral data collection, feature importance, supervised classification, and model validation for continuous user authentication.

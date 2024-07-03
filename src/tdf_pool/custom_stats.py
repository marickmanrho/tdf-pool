import numpy as np
import pandas as pd


def custom_binary_classifications(y_true, y_pred, n: int = 15):
    tt = np.argsort(y_true)
    tp = np.argsort(y_pred)

    true_treshold = y_true[tt[-n]]
    pred_treshold = y_pred[tp[-n]]

    true_positive = np.where(
        np.logical_and(y_true >= true_treshold, y_pred >= pred_treshold)
    )[0]
    false_positive = np.where(
        np.logical_and(y_true < true_treshold, y_pred >= pred_treshold)
    )[0]
    false_negative = np.where(
        np.logical_and(y_true >= true_treshold, y_pred < pred_treshold)
    )[0]
    true_negative = np.where(
        np.logical_and(y_true < true_treshold, y_pred < pred_treshold)
    )[0]

    TP = len(true_positive)
    FP = len(false_positive)
    FN = len(false_negative)
    TN = len(true_negative)
    return TP, FP, FN, TN


def custom_confusion_matrix(y_true, y_pred, n: int = 15):
    TP, FP, FN, TN = custom_binary_classifications(y_true, y_pred, n)

    true_idx = pd.MultiIndex.from_tuples([("Actual", "True"), ("Actual", "False")])
    pred_idx = pd.MultiIndex.from_tuples(
        [("Prediction", "True"), ("Prediction", "False")]
    )

    df = pd.DataFrame(
        data=[[TP, FP], [FN, TN]],
        index=true_idx,
        columns=pred_idx,
    )
    return df


def custom_f_score(y_true, y_pred, n: int = 15, beta: float = 1.0):
    TP, FP, FN, _ = custom_binary_classifications(y_true, y_pred, n)

    F = (1 + beta**2) * TP / ((1 + beta**2) * TP + beta**2 * FN + FP)
    return F

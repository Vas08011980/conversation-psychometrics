# Three preregistered tests for language indicators (run after pipeline.py).
# (i)  Convergence: within-person r(indicator, own EMA) >= .20 AND above r with every other EMA construct
# (ii) Robustness: (i) still holds controlling for message length AND with topic words masked
# (iii) Human agreement: two blind raters agree (ICC >= .60) and indicator tracks their mean (r >= .30)
# Usage: Rscript tests/tests.R demo/out demo/data
args <- commandArgs(TRUE); out <- if (length(args)) args[1] else "demo/out"
dat <- if (length(args) > 1) args[2] else "demo/data"
R_MIN <- .20; ICC_MIN <- .60; R_RATER <- .30; B <- 1000; set.seed(2026)

d   <- read.csv(file.path(out, "day_scores.csv"))
ema <- read.csv(file.path(dat, "ema.csv"))
ema <- reshape(ema, idvar = c("id", "day"), timevar = "construct", direction = "wide")
names(ema) <- sub("^score\\.", "", names(ema))
m <- merge(d, ema, by = c("id", "day"))
C <- c("loneliness", "stress", "mood", "self_esteem")
wc <- function(x) x - ave(x, m$id, FUN = function(v) mean(v, na.rm = TRUE))     # within-person centring
resid_len <- function(x) residuals(lm(wc(x) ~ wc(m$n_chars)))

r_within <- function(ind, ema_c, idx = seq_len(nrow(m))) cor(ind[idx], ema_c[idx], use = "complete.obs")
boot_ci <- function(ind, ema_c) {            # cluster bootstrap over persons
  ids <- unique(m$id); rows <- split(seq_len(nrow(m)), m$id)
  r <- replicate(B, { s <- unlist(rows[sample(ids, replace = TRUE)]); r_within(ind, ema_c, s) })
  quantile(r, c(.025, .975), na.rm = TRUE)
}
test_conv <- function(ind) {
  r <- sapply(C, function(o) r_within(ind, wc(m[[o]])))
  r
}

res <- do.call(rbind, lapply(C, function(c) {
  raw <- wc(m[[paste0("ind_", c)]]); len <- resid_len(m[[paste0("ind_", c)]])
  msk <- wc(m[[paste0("ind_", c, "_masked")]])
  r_raw <- test_conv(raw); r_len <- test_conv(len); r_msk <- test_conv(msk)
  ci <- boot_ci(raw, wc(m[[c]]))
  pass_i  <- r_raw[c] >= R_MIN && r_raw[c] > max(r_raw[setdiff(C, c)])
  pass_ii <- all(c(r_len[c], r_msk[c]) >= R_MIN) && r_len[c] > max(r_len[setdiff(C, c)]) &&
             r_msk[c] > max(r_msk[setdiff(C, c)])
  data.frame(construct = c, r_within = round(r_raw[c], 3), ci_low = round(ci[1], 3), ci_high = round(ci[2], 3),
             max_r_other = round(max(r_raw[setdiff(C, c)]), 3), r_length_controlled = round(r_len[c], 3),
             r_topic_masked = round(r_msk[c], 3), pass_convergence = pass_i, pass_robustness = pass_ii)
}))

# (iii) Human agreement. DEMO ONLY: raters are simulated from what the day's text actually voices
# (share of messages expressing the construct) plus rater noise;
# in a real study two trained raters code rating_sample_LOCAL_ONLY.csv blind to EMA and indicators.
truth <- read.csv(file.path(dat, "truth.csv"))
samp <- merge(read.csv(file.path(out, "rating_sample_LOCAL_ONLY.csv"))[, c("id", "day")], truth, by = c("id", "day"))
samp <- merge(samp, d, by = c("id", "day"))
icc21 <- function(a, b) { x <- cbind(a, b); n <- nrow(x); k <- 2; mr <- rowMeans(x); mc <- colMeans(x); g <- mean(x)
  msr <- k * sum((mr - g)^2) / (n - 1); msc <- n * sum((mc - g)^2) / (k - 1)
  mse <- sum((x - outer(mr, rep(1, k)) - outer(rep(1, n), mc) + g)^2) / ((n - 1) * (k - 1))
  (msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n) }
agree <- do.call(rbind, lapply(C, function(c) {
  t <- scale(samp[[paste0("shown_", c)]])[, 1]; r1 <- t + rnorm(length(t), 0, .5); r2 <- t + rnorm(length(t), 0, .5)
  icc <- icc21(r1, r2); r_ind <- cor(samp[[paste0("ind_", c)]], (r1 + r2) / 2)
  data.frame(construct = c, rater_icc = round(icc, 3), r_indicator_raters = round(r_ind, 3),
             pass_agreement = icc >= ICC_MIN && r_ind >= R_RATER)
}))
res <- merge(res, agree, by = "construct")
res$all_three_pass <- res$pass_convergence & res$pass_robustness & res$pass_agreement
res <- res[match(C, res$construct), ]
write.csv(res, file.path(out, "test_results.csv"), row.names = FALSE)
print(res, row.names = FALSE)

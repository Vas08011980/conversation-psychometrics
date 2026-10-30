# Three prespecified tests for language indicators (run after pipeline.py).
# (i)  Convergence: within-person r(indicator, own EMA) >= .20 AND above r with every other EMA construct
# (ii) Robustness: (i) still holds controlling for message length AND with topic words masked
# (iii) Human agreement: two blind raters agree (ICC >= .60) and indicator tracks their mean (r >= .30)
# Usage: Rscript tests/tests.R <pipeline output folder> <data folder>   e.g. Rscript tests/tests.R demo/out demo/data
# The data folder holds ema.csv (id, day, construct, score) and, for test (iii) on real data,
# ratings.csv (id, day, construct, rater1, rater2). Constructs are taken from ema.csv.
args <- commandArgs(TRUE); out <- if (length(args)) args[1] else "demo/out"
dat <- if (length(args) > 1) args[2] else "demo/data"
R_MIN <- .20; ICC_MIN <- .60; R_RATER <- .30; B <- 1000; set.seed(2026)

d   <- read.csv(file.path(out, "day_scores.csv"))
ema <- read.csv(file.path(dat, "ema.csv"))
C <- unique(ema$construct)                      # constructs, in the order they appear in ema.csv
ema <- reshape(ema, idvar = c("id", "day"), timevar = "construct", direction = "wide")
names(ema) <- sub("^score\\.", "", names(ema))
m <- merge(d, ema, by = c("id", "day"))
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

# (iii) Human agreement. Two trained raters code rating_sample_LOCAL_ONLY.csv blind to EMA and indicators.
# Real study: save their codes as <data folder>/ratings.csv with columns id, day, construct, rater1, rater2.
# Demo (no ratings.csv, simulated truth.csv present): raters are simulated from what the day's text
# actually voices (share of messages expressing the construct) plus rater noise.
icc21 <- function(a, b) { x <- cbind(a, b); n <- nrow(x); k <- 2; mr <- rowMeans(x); mc <- colMeans(x); g <- mean(x)
  msr <- k * sum((mr - g)^2) / (n - 1); msc <- n * sum((mc - g)^2) / (k - 1)
  mse <- sum((x - outer(mr, rep(1, k)) - outer(rep(1, n), mc) + g)^2) / ((n - 1) * (k - 1))
  (msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n) }
samp <- merge(read.csv(file.path(out, "rating_sample_LOCAL_ONLY.csv"))[, c("id", "day")], d, by = c("id", "day"))
rat_file <- file.path(dat, "ratings.csv"); truth_file <- file.path(dat, "truth.csv")
if (file.exists(rat_file)) {                      # real raters
  rat <- read.csv(rat_file)
  get_ratings <- function(c) {
    x <- merge(samp, rat[rat$construct == c, c("id", "day", "rater1", "rater2")], by = c("id", "day"))
    list(r1 = x$rater1, r2 = x$rater2, ind = x[[paste0("ind_", c)]])
  }
  message("Test (iii): using rater codes from ", rat_file)
} else if (file.exists(truth_file)) {             # simulated demo
  samp <- merge(samp, read.csv(truth_file), by = c("id", "day"))
  get_ratings <- function(c) {
    t <- scale(samp[[paste0("shown_", c)]])[, 1]
    list(r1 = t + rnorm(length(t), 0, .5), r2 = t + rnorm(length(t), 0, .5), ind = samp[[paste0("ind_", c)]])
  }
  message("Test (iii): DEMO - raters simulated from truth.csv (no ratings.csv found)")
} else {
  get_ratings <- NULL
  message("Test (iii) not run: add ratings.csv (id, day, construct, rater1, rater2) to ", dat)
}
agree <- do.call(rbind, lapply(C, function(c) {
  if (is.null(get_ratings))
    return(data.frame(construct = c, rater_icc = NA, r_indicator_raters = NA, pass_agreement = NA))
  g <- get_ratings(c); ok <- complete.cases(g$r1, g$r2, g$ind)
  if (sum(ok) < 3) stop("Too few rated conversation-days for construct '", c, "' in ratings.csv")
  icc <- icc21(g$r1[ok], g$r2[ok]); r_ind <- cor(g$ind[ok], (g$r1[ok] + g$r2[ok]) / 2)
  data.frame(construct = c, rater_icc = round(icc, 3), r_indicator_raters = round(r_ind, 3),
             pass_agreement = icc >= ICC_MIN && r_ind >= R_RATER)
}))
res <- merge(res, agree, by = "construct")
res$all_three_pass <- res$pass_convergence & res$pass_robustness & res$pass_agreement
res <- res[match(C, res$construct), ]
write.csv(res, file.path(out, "test_results.csv"), row.names = FALSE)
print(res, row.names = FALSE)

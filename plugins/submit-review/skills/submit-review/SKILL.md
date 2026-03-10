---
name: submit-review
description: Post a code review with line-level comments to a GitHub PR. Use when the user asks to "submit a review", "post review comments", "add review to PR", or "submit review" and you already have findings to post.
license: MIT
metadata:
  author: github.com/ffalor
  version: "1.0"
---

# Post PR Review

Submit a code review with line-level comments to a GitHub PR using `gh api`.

## When to Use

Use this skill when the user wants to post review comments to a GitHub PR. This skill handles the mechanics of submitting the review, not the review analysis itself.

## Instructions

1. **Identify the PR**
   - Extract owner, repo, and PR number from the provided URL or context
   - Get the head commit SHA: `gh pr view {number} --repo {owner}/{repo} --json headRefOid -q .headRefOid`

2. **Build the review JSON**
   - Write a JSON file to `/tmp/review.json` with this structure:
   ```json
   {
     "body": "Review summary",
     "event": "COMMENT",
     "commit_id": "<head_commit_sha>",
     "comments": [
       {
         "path": "relative/file/path",
         "line": 25,
         "body": "Comment text"
       }
     ]
   }
   ```
   - `event` must be one of: `COMMENT`, `APPROVE`, or `REQUEST_CHANGES`
   - `line` is the line number in the diff (right side)
   - `path` is relative to the repo root
   - Ask the user which `event` type to use if not specified

3. **Post the review**
   ```bash
   gh api repos/{owner}/{repo}/pulls/{number}/reviews --input /tmp/review.json
   ```

4. **Clean up**
   - Remove `/tmp/review.json`
   - Return the review URL from the response `html_url` field

## Important Notes

- The `--input` flag is required for the comments array. Using `-f` passes it as a string, not an array, and the API will reject it.
- The `commit_id` must match the PR's head commit.
- Line numbers refer to the final state of the file (right side of the diff).

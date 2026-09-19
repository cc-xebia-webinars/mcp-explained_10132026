# Release Checklist

We run through this list before every production release of the storefront.

1. Confirm every pull request in the release has an approving review.
2. Check that no open issues are labeled `release-blocker`.
3. Tag the release in GitHub using the `vYYYY.MM.DD` format.
4. Deploy the new image as a new Azure Container Apps revision with 0% of traffic.
5. Run the smoke tests against the new revision's direct URL.
6. Shift traffic to the new revision in two steps: 20%, then 100%.
7. If the smoke tests fail or errors climb, roll back by sending all traffic to the previous revision.
8. Post the release notes in `#storefront`.

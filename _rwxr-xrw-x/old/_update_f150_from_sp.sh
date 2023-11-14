set -x

SOURCE_BRANCH="sp-f150-dev"
TARGET_BRANCH="f150"
git checkout ${SOURCE_BRANCH}
git branch -D ${TARGET_BRANCH}
# git push origin --delete ${TARGET_BRANCH}
git branch ${TARGET_BRANCH}
git checkout ${TARGET_BRANCH}
# git cherry-pick df1e3af8d2e1f55a74163d1112f9941bdc2a77f4
# git cherry-pick ba27e55360fe1b1a166577ff527455dda44ab014
git push --set-upstream origin ${TARGET_BRANCH} --force

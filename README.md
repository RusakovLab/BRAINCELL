# BrainCell

BrainCell platform for neuronal simulations.

Our software packages are open for you to download, install, and explore under the permissive 3-clause BSD license.

Based on [BrainCellNew](https://github.com/LeonidSavtchenko/BrainCellNew) by Leonid Savtchenko.

---

## Git Workflow Guide for the BrainCell Project

### 1. Daily Workflow

#### Before Starting

Make sure you are on the correct branch:

- `main` —  stable development
- `ModifyBrainCell` — experiments and risky modifications

You can check or switch branches in GitHub Desktop or using:

```bash
git branch
git checkout main
```

#### Saving Changes (Commit)

After making a small, working modification:

1. Write a clear commit message.
2. Click **Commit** (or run `git commit`).
3. This creates a restore point in the project history.

Example:

```bash
git add .
git commit -m "Fixed LFP kernel distance normalization"
```

#### Discarding Changes

If something breaks:

- In **GitHub Desktop**: Right-click the file in the *Changes* list → **Discard changes**
- Or via terminal:

```bash
git restore filename.py
```

---

### 2. Working with Branches

#### Creating a Branch

Use branches for experiments or structural refactoring:

- **GitHub Desktop**: Branch → New Branch
- Or via terminal:

```bash
git checkout -b new-feature-branch
```

#### Switching Branches

Switching branches replaces the actual project files on disk with the selected branch version.

```bash
git checkout main
```

#### Merging Branches

When work in `ModifyBrainCell` is validated:

1. Switch to `main`
2. Merge the experimental branch

```bash
git checkout main
git merge ModifyBrainCell
```

In **GitHub Desktop**: Branch → Merge into current branch

---

### 3. Cleaning the Project (.gitignore)

To prevent heavy simulation results from being tracked, add the following lines to `.gitignore`:

```
Binary results/
Text results/
_temp_matlab/
```

This keeps the repository clean and lightweight.

---

### 4. Useful Git Features

#### Stash

Temporarily store unfinished changes without committing them:

```bash
git stash
git stash pop
```

Useful when you need to quickly switch branches.

#### Tag

Mark important milestones in project history:

```bash
git tag v1.0
git push origin v1.0
```

In **GitHub Desktop**: History → Create Tag

#### Export Without Git History

To create a clean copy of the project without version history:

**Option 1:**

```bash
git archive --format zip --output BrainCell.zip main
```

**Option 2:** Delete the hidden `.git` folder manually.

---

## License

This project is licensed under the BSD 3-Clause License — see the [LICENSE](LICENSE) file for details.

## Contact

Rusakov Lab — [GitHub](https://github.com/RusakovLab)

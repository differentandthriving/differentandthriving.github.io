# Different & Thriving

Personal profile site for **Tiffany Gibson**, a neurodiversity family coach, at [differentandthriving.com](https://differentandthriving.com).

## Stack

- Jekyll 4.4.1
- Beautiful Jekyll 6.0.1 through its remote-theme integration
- Bootstrap components/utilities supplied by Beautiful Jekyll
- One Jekyll plugin: `jekyll-remote-theme`

Run a local preview with Ruby 3.3.13 and Bundler:

```sh
bundle install
bundle exec jekyll serve
```

The site builds and deploys through GitHub Actions on pushes to `main`. In the repository's **Settings → Pages**, select **GitHub Actions** as the publishing source. The workflow uses read-only permissions for building and the minimum Pages permissions for deployment.

## Content placeholders

The bio, audience, approach, service, FAQ, and contact copy are intentionally marked as placeholders. Replace them with Tiffany's approved wording before publishing. The text-only navbar name is a temporary wordmark until a logo is supplied. Local plans and palette boards are kept under `plans/`; Git ignores them and Jekyll excludes them from the published site.

The supplied brain illustration files are preserved under `assets/img/`; the existing `brain-types.svg` is the selected hero art. The other available illustrations are not used in this first pass because their brighter colors compete with the chosen palette.

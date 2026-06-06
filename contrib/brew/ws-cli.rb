class WsCli < Formula
  include Language::Python::Virtualenv

  desc "AI-native cross-project workspace manager — the Forge OS project hub"
  homepage "https://github.com/modib/ws-cli"
  url "https://github.com/modib/ws-cli/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "0019dfc4b32d63c1392aa264aed2253c1e0c2fb09216f8e2cc269bbfb8bb49b5"
  license "MIT"

  depends_on "python@3.14"

  def install
    venv = virtualenv_create(libexec)
    venv.pip_install_and_link buildpath
  end

  test do
    system "#{bin}/ws", "--version"
  end
end

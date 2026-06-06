class WsCli < Formula
  include Language::Python::Virtualenv

  desc "AI-native cross-project workspace manager — the Forge OS project hub"
  homepage "https://github.com/modib/ws-cli"
  url "https://github.com/modib/ws-cli/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "12398d17e30ee3aa58451bfe6ced2c28c3d367b489b229c9718933ed1ee6b57d"
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

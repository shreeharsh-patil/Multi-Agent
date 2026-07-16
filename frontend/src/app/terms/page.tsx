import Link from "next/link"

export default function TermsPage() {
  return (
    <div className="bg-[#F5F4F0] text-[#111] min-h-screen font-sans antialiased">
      {/* Simple top nav */}
      <div className="fixed top-4 inset-x-0 z-50 flex justify-center px-4 pointer-events-none">
        <nav className="pointer-events-auto w-full max-w-6xl flex items-center justify-between px-5 py-3 rounded-2xl border border-black/[0.06] bg-[#F5F4F0]/30"
          style={{ backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", boxShadow: "0 8px 32px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.06)" }}
        >
          <Link href="/" className="font-pixel text-xs tracking-[0.25em] text-black/70 hover:text-black transition-colors">AGENTIC</Link>
          <Link href="/" className="text-[11px] text-black/60 hover:text-black transition-colors tracking-wide">
            ← Back to home
          </Link>
        </nav>
      </div>

      <div className="pt-24 px-6 md:px-12 lg:px-20 pb-20">
        <div className="max-w-3xl mx-auto">
          <div className="mb-12">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] tracking-widest font-sans text-black/40 bg-black/[0.04]">
              LEGAL
            </span>
            <h1 className="mt-5 text-4xl md:text-5xl font-light tracking-tight leading-[1.05]">
              Terms of Service
            </h1>
            <p className="mt-4 text-sm text-black/35">Last updated: July 2026</p>
          </div>

          <div className="space-y-8 text-sm text-black/55 leading-relaxed">
            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">1. Acceptance of Terms</h2>
              <p className="mb-3">
                By accessing or using the Agentic platform, you agree to be bound by these Terms 
                of Service. If you do not agree to these terms, please do not use the service.
              </p>
              <p>
                We reserve the right to update these terms at any time. Continued use of the 
                platform after changes constitutes acceptance of the new terms.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">2. Account Registration</h2>
              <p className="mb-3">
                You must create an account to use our services. You are responsible for maintaining 
                the confidentiality of your account credentials and for all activities under your account.
              </p>
              <p>
                You must provide accurate, current, and complete information during registration. 
                You may not create accounts through unauthorized means, including bots or automated tools.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">3. Acceptable Use</h2>
              <p className="mb-3">
                You agree to use the platform only for lawful purposes and in accordance with these 
                terms. You may not use the platform to:
              </p>
              <ul className="list-disc pl-5 space-y-2 mb-3">
                <li>Violate any applicable laws or regulations</li>
                <li>Infringe upon the rights of others</li>
                <li>Distribute malware or harmful content</li>
                <li>Attempt to bypass rate limits or security measures</li>
                <li>Use the service for automated high-volume queries without authorization</li>
              </ul>
              <p>
                We reserve the right to suspend or terminate accounts that violate these terms.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">4. Intellectual Property</h2>
              <p className="mb-3">
                You retain ownership of the content you upload, create, or process through the platform. 
                By using the service, you grant us a limited license to process your content as 
                necessary to provide the service.
              </p>
              <p>
                The Agentic platform, including its software, branding, and design, is protected 
                by intellectual property laws. You may not copy, modify, or reverse-engineer 
                any part of the platform without our explicit consent.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">5. Service Limitations</h2>
              <p className="mb-3">
                We strive to provide reliable service but do not guarantee uninterrupted availability. 
                The platform is provided &ldquo;as is&rdquo; without warranties of merchantability or fitness 
                for a particular purpose.
              </p>
              <p>
                AI agent outputs are generated algorithmically and may contain errors or inaccuracies. 
                You should review and verify important outputs before relying on them.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">6. Limitation of Liability</h2>
              <p>
                To the maximum extent permitted by law, Agentic shall not be liable for any indirect, 
                incidental, special, or consequential damages arising from your use of the platform, 
                including but not limited to loss of data, revenue, or business opportunity.
              </p>
            </section>

            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">7. Contact</h2>
              <p>
                For questions about these terms, please contact us at{' '}
                <a href="mailto:legal@agentic.dev" className="text-black/70 underline underline-offset-2 hover:text-black transition-colors">
                  legal@agentic.dev
                </a>.
              </p>
            </section>
          </div>

          {/* Footer */}
          <div className="mt-20 pt-8 border-t border-black/[0.04]">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <span className="font-pixel text-xs tracking-[0.25em] text-black/40">AGENTIC</span>
              <div className="flex items-center gap-6">
                <Link href="/privacy" className="text-xs text-black/35 hover:text-black/70 transition-colors tracking-widest">Privacy</Link>
                <Link href="/terms" className="text-xs text-black/35 hover:text-black/70 transition-colors tracking-widest">Terms</Link>
                <Link href="/docs" className="text-xs text-black/35 hover:text-black/70 transition-colors tracking-widest">Docs</Link>
                <a href="https://github.com/shreeharsh-patil/Multi-Agent" target="_blank" rel="noopener noreferrer" className="text-xs text-black/35 hover:text-black/70 transition-colors tracking-widest">GitHub</a>
              </div>
            </div>
            <div className="mt-4">
              <span className="text-xs text-black/20">&copy; 2026 Agentic. All rights reserved.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

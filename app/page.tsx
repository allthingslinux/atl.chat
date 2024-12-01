import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { DiscIcon as Discord, MessageSquare, Signal, Share2, MessageCircle } from 'lucide-react'
import Link from "next/link"

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen bg-background">
      <header className="px-4 lg:px-6 h-16 flex items-center border-b justify-center">
        <Link className="flex items-center justify-center" href="/">
          <MessageCircle className="h-6 w-6 mr-2" />
          <span className="font-bold">atl.chat</span>
        </Link>
      </header>
      <main className="flex-grow container mx-auto px-4 py-16">
        <div className="flex flex-col items-center text-center space-y-4 mb-16">
          <h1 className="text-4xl font-bold tracking-tighter sm:text-5xl">Connect with All Things Linux</h1>
          <p className="text-muted-foreground max-w-[600px] md:text-xl">
            Join our vibrant Linux community across multiple chat platforms
          </p>
          <Button asChild size="lg" className="mt-4">
            <Link href="https://discord.gg/linux">
              <Discord className="mr-2 h-5 w-5" />
              Join our Discord
            </Link>
          </Button>
        </div>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center text-primary-foreground">
                <MessageSquare className="h-5 w-5 mr-2" />
                IRC
              </CardTitle>
              <CardDescription>Classic real-time chat protocol</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">Connect via your favorite IRC client</p>
              <code className="bg-background text-primary-foreground px-2 py-1 rounded text-sm">irc.atl.chat/6697 #general</code>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center text-primary-foreground">
                <Share2 className="h-5 w-5 mr-2" />
                XMPP
              </CardTitle>
              <CardDescription>Open communication protocol</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">Join our XMPP chatroom</p>
              <code className="bg-background text-primary-foreground px-2 py-1 rounded text-sm">general@muc.atl.chat</code>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center text-primary-foreground">
                <Signal className="h-5 w-5 mr-2" />
                Signal
              </CardTitle>
              <CardDescription>Secure messaging platform</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">Join our Signal group</p>
              <code className="bg-background text-primary-foreground px-2 py-1 rounded text-sm">https://signal.atl.chat</code>
            </CardContent>
          </Card>
        </div>
        <div className="mt-16 text-center">
          <h2 className="text-2xl font-bold mb-4">Someday Maybe?</h2>
          <div className="flex justify-center gap-4 flex-wrap">
            <Badge variant="outline" className="text-sm">Mastodon</Badge>
            <Badge variant="outline" className="text-sm">Matrix</Badge>
          </div>
        </div>
      </main>
      <footer className="border-t border-secondary/50 p-4">
        <div className="flex flex-row items-center justify-center h-8">
          <p className="text-sm text-muted-foreground text-balance text-center">
            © {new Date().getFullYear()} All Things Linux. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  )
}
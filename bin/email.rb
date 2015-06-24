require 'mail'

def sendmail(filename, title, hostname)
  return unless hostname.include?("id774.net")

  options = {
    :address  => "localhost",
    :port   => 25,
    :authentication => 'plain',
    :enable_starttls_auto => true
  }

  Mail.defaults do
    delivery_method :smtp, options
  end

  dir = File.expand_path(File.dirname(__FILE__))
  path = File.join(dir, "..", "data", filename)

  mail = Mail.new do
    from     "finance@#{hostname}"
    to       "finance@id774.net"
    subject  title
    body     File.read(path)
  end

  mail.charset = 'utf-8'
  mail.delivery_method :sendmail
  mail.deliver!
end

if __FILE__ == $0
  hostname = `hostname`.chop
  today = Time.now.strftime("%a %d %b %Y")

  filename = ARGV.shift || "summary.csv"
  report_name = ARGV.shift || "Summary Report of Financial Data"

  title = "[cron][#{hostname}] #{report_name} on #{today}"
  sendmail(filename, title, hostname)
end

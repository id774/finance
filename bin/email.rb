require 'mail'

def sendmail
  hostname = `hostname`.chop
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

  filename = "summary.csv"
  dir = File.expand_path(File.dirname(__FILE__))
  path = File.join(dir, "..", "data", filename)

  today = Time.now.strftime("%a %d %b %Y")

  mail = Mail.new do
    from     "finance@#{hostname}"
    to       "finance@id774.net"
    subject  "[cron][#{hostname}] Summary Report of Financial Data on #{today}"
    body     File.read(path)
  end

  mail.charset = 'utf-8'
  mail.delivery_method :sendmail
  mail.deliver!
end

if __FILE__ == $0
  sendmail
end

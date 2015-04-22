require 'mail'

def sendmail
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

  mail = Mail.new do
    from     "finance@harpuia.id774.net"
    to       "finance@id774.net"
    subject  "Summary Report of Financial Data"
    body     File.read(path)
  end

  mail.charset = 'utf-8'
  mail.delivery_method :sendmail
  mail.deliver!
end

if __FILE__ == $0
  hostname = `hostname`.chop
  if hostname.include?("id774.net")
    puts "Sending Summary Report from id774.net"
    sendmail
  end
end

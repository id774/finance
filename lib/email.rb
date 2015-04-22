require 'mail'

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
  from     "finance@id774.net"
  to       "774@id774.net"
  subject  "Summary of Finance Data"
  body     File.read(path)
end

mail.charset = 'utf-8'
mail.delivery_method :sendmail
mail.deliver!

# Read-only integrity summary of transactions per account, run inside Sure's web container.
# Prints counts, date ranges and duplicate-group counts; no descriptions or amounts.
# Duplicate = same account, date, amount and name. Two identical same-day charges are
# legitimate duplicates too, so review any hit in the UI before deleting anything.
txns = Entry.where(entryable_type: "Transaction")
puts "SURE accounts=#{Account.count} transactions=#{txns.count} imports=#{Import.count}"
Account.order(:created_at).each do |a|
  e = txns.where(account_id: a.id)
  n = e.count
  if n.zero?
    puts format("%-32s txns=0", a.name.to_s[0, 32])
    next
  end
  dups = e.group(:date, :amount, :name).having("COUNT(*) > 1").count
  puts format("%-32s txns=%d imported=%d range=%s..%s dup_groups=%d extra_rows=%d",
              a.name.to_s[0, 32], n, e.where.not(import_id: nil).count,
              e.minimum(:date), e.maximum(:date), dups.size, dups.values.sum - dups.size)
end
Import.order(:created_at).last(5).each do |i|
  puts "import #{i.id.to_s[0, 8]} type=#{i.type} status=#{i.status} rows=#{i.rows_count} created=#{i.created_at.to_date}"
end

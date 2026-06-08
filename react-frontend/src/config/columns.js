export const BOOKING_COLUMNS = [
  { key:'id', label:'ID' }, { key:'customer_name', label:'Customer' }, { key:'mobile_number', label:'Mobile' },
  { key:'outlet_name', label:'Outlet' }, { key:'sales_executive_name', label:'Executive' }, { key:'variant_name', label:'Variant' },
  { key:'booking_date', label:'Booking Date' }, { key:'booking_amt', label:'Booking Amount', type:'money' },
  { key:'price_offered_booking', label:'Price Offered', type:'money' }, { key:'total_discount_booking', label:'Total Discount', type:'money' },
  { key:'excess_booking', label:'Excess', type:'money' }, { key:'status', label:'Status' }
];
export const DELIVERY_COLUMNS = [
  { key:'id', label:'ID' }, { key:'customer_name', label:'Customer' }, { key:'mobile_number', label:'Mobile' },
  { key:'outlet_name', label:'Outlet' }, { key:'variant_name', label:'Variant' }, { key:'booking_date', label:'Booking Date' },
  { key:'delivery_date', label:'Delivery Date' }, { key:'invoice_number', label:'Invoice No.' },
  { key:'total_receivable', label:'Receivable', type:'money' }, { key:'total_received', label:'Received', type:'money' },
  { key:'balance', label:'Balance', type:'money' }, { key:'total_excess_discount', label:'Excess Discount', type:'money' },
  { key:'payment_status', label:'Payment Status' }
];
export const COMPLAINT_COLUMNS = [
  'code','date_of_complaint','dealer','showroom','customer_name','complainant_name','point_of_complaint','status','flag'
];
export const DETAIL_SECTIONS = [
  { title:'Customer Details', fields:['customer_name','mobile_number','alternate_mobile','email','pan_number','aadhar_number','address','city','pin_code'] },
  { title:'Vehicle & Booking', fields:['variant_id','outlet_id','sales_executive_id','booking_date','booking_amt','booking_receipt_num','model_year','team_leader','customer_file_number'] },
  { title:'Delivery & Invoice', fields:['delivery_date','invoice_number','vin_number','engine_number','color','registration_number','registration_date','total_receivable','total_received','balance','payment_status'] },
  { title:'Audit Summary', fields:['price_offered_booking','discount_booking','total_discount_booking','excess_booking','adjustment_booking','total_actual_discount','total_allowed_discount','total_excess_discount','other_discount_delivery','adjustment_delivery','status'] }
];

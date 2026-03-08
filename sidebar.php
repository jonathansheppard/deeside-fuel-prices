<aside class="col-md-4 col-sm-12 sidebar">
     

                <!-- search wrap -->
           <div class="search-wrapper">
                    <span><? echo date_i18n("l F jS G:i"); ?></span>
                  <br>
                  <br>
                  

                    <br>
                    <span><a href="https://www.deeside.com/contact">Get In Touch</a> / <a href="https://www.deeside.com/do-you-want-to-speak-to-the-largest-most-engaged-audience-in-the-area/">Advertise Now</a> </span>
                    
 			<form class="sidebar-search" action="https://www.deeside.com" role="search" method="get" > 					
<input type="text"  name="s" placeholder="Search..." > 	
              	    <input type="hidden" value="post" name="post_type" id="post_type" />

					     <input type="hidden" value="date" name="order_by" id="order_by" />
					<input type="submit" value="">
 
            </form>
         </div>

<!-- Fuel Price Widget -->
<div class="shadow-lg p-3 mb-5 bg-gray rounded">
  <h5 class="title title-small flex-center-side">⛽ Local Fuel Prices</h5>
  <div id="fuel-widget" style="font-family:Arial,sans-serif;font-size:14px;line-height:1.6">
    <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eee">
      <span>🟢 Cheapest unleaded</span>
      <strong id="fw-cheapest" style="color:#16a34a">—</strong>
    </div>
    <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eee">
      <span>🔴 Most expensive</span>
      <strong id="fw-highest" style="color:#dc2626">—</strong>
    </div>
    <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eee">
      <span>🇬🇧 UK average</span>
      <strong id="fw-avg" style="color:#666">—</strong>
    </div>
    <div style="padding:8px 0;font-size:12px;color:#888" id="fw-station"></div>
    <a href="https://deeside-fuel-prices.netlify.app/" target="_blank" 
       style="display:block;text-align:center;background:#1a1d28;color:#fff;padding:10px;border-radius:6px;text-decoration:none;font-weight:bold;margin-top:8px">
      View full fuel price map →
    </a>
    <div style="font-size:10px;color:#aaa;text-align:center;margin-top:6px" id="fw-updated">
      Data from GOV.UK Fuel Finder Scheme
    </div>
  </div>
  <script>
  fetch('https://deeside-fuel-prices.netlify.app/stations.json?t='+Date.now())
    .then(r=>r.json()).then(d=>{
      const now=Date.now();
      const fresh=d.stations.filter(s=>{
        if(!s.unleaded||s.unleaded<=0)return false;
        if(!s.updated)return false;
        const hrs=(now-new Date(s.updated).getTime())/3600000;
        return hrs<120; // exclude 5 days+ stale
      }).sort((a,b)=>a.unleaded-b.unleaded);
      if(fresh.length){
        document.getElementById('fw-cheapest').textContent=fresh[0].unleaded.toFixed(1)+'p';
        document.getElementById('fw-highest').textContent=fresh[fresh.length-1].unleaded.toFixed(1)+'p';
        document.getElementById('fw-avg').textContent=d.nationalAvg.unleaded.toFixed(1)+'p';
        document.getElementById('fw-station').textContent='Cheapest: '+fresh[0].name;
        const dt=new Date(d.lastUpdated);
        document.getElementById('fw-updated').textContent='Updated '+dt.toLocaleString('en-GB',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
      }
    }).catch(()=>{});
  </script>
</div>
<!-- End Fuel Price Widget -->
         
<!DOCTYPE html>
       
                      




          
          <div class="shadow-lg p-3 mb-5 bg-gray rounded">

<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8373809220012309"
     crossorigin="anonymous"></script>
<!-- infill 2 -->
<ins class="adsbygoogle"
     style="display:block"
     data-ad-client="ca-pub-8373809220012309"
     data-ad-slot="5535072674"
     data-ad-format="auto"
     data-full-width-responsive="true"></ins>
<script>
     (adsbygoogle = window.adsbygoogle || []).push({});
</script>
           

          </div>

<div class="shadow-lg p-3 mb-5 bg-gray rounded">

          
	          
	          <?php include("/var/www/html/wordpress/mixergrab/rssmixer-deeside.txt"); ?>



	           <a href="https://www.deeside.com/north-wales-news-headlines"><button type="button" class="btn-outline-success btn-sm btn-block">

<svg height="24" viewBox="0 0 457.14286 457.14286" width="24" xmlns="http://www.w3.org/2000/svg"><path d="m427.8125 0h-398.480469c-16.171875 0-29.332031 13.160156-29.332031 29.332031v398.480469c0 16.167969 13.160156 29.332031 29.332031 29.332031h288.75c2.425781 0 4.75-.964843 6.460938-2.679687l129.921875-129.921875c1.714844-1.710938 2.679687-4.035157 2.679687-6.460938v-288.75c0-16.171875-13.164062-29.332031-29.332031-29.332031zm-409.527344 427.8125v-398.480469c0-6.089843 4.957032-11.046875 11.046875-11.046875h398.480469c6.089844 0 11.042969 4.957032 11.042969 11.046875v279.605469h-100.585938c-16.171875 0-29.332031 13.160156-29.332031 29.332031v100.585938h-279.605469c-6.089843 0-11.046875-4.953125-11.046875-11.042969zm407.644532-100.589844-98.707032 98.707032v-87.660157c0-6.089843 4.957032-11.046875 11.046875-11.046875zm0 0"/><path d="m54.855469 176.839844h347.429687c5.054688 0 9.144532-4.089844 9.144532-9.144532 0-5.050781-4.089844-9.140624-9.144532-9.140624h-347.429687c-5.050781 0-9.140625 4.089843-9.140625 9.140624 0 5.054688 4.089844 9.144532 9.140625 9.144532zm0 0"/><path d="m54.855469 232.222656h347.429687c5.054688 0 9.144532-4.089844 9.144532-9.140625 0-5.054687-4.089844-9.144531-9.144532-9.144531h-347.429687c-5.050781 0-9.140625 4.089844-9.140625 9.144531 0 5.050781 4.089844 9.140625 9.140625 9.140625zm0 0"/><path d="m54.855469 287.605469h347.429687c5.054688 0 9.144532-4.085938 9.144532-9.140625 0-5.054688-4.089844-9.144532-9.144532-9.144532h-347.429687c-5.050781 0-9.140625 4.089844-9.140625 9.144532 0 5.054687 4.089844 9.140625 9.140625 9.140625zm0 0"/><path d="m54.855469 342.992188h217.511719c5.050781 0 9.140624-4.089844 9.140624-9.144532 0-5.054687-4.089843-9.140625-9.140624-9.140625h-217.511719c-5.050781 0-9.140625 4.085938-9.140625 9.140625 0 5.054688 4.089844 9.144532 9.140625 9.144532zm0 0"/><path d="m272.367188 380.089844h-217.511719c-5.050781 0-9.140625 4.089844-9.140625 9.140625 0 5.054687 4.089844 9.144531 9.140625 9.144531h217.511719c5.050781 0 9.140624-4.089844 9.140624-9.144531 0-5.050781-4.089843-9.140625-9.140624-9.140625zm0 0"/><path d="m111.476562 91.363281 25.910157 41.910157h13.019531v-64.269532h-12.054688v42.917969l-26.304687-42.917969h-12.625v64.269532h12.054687zm0 0"/><path d="m213.007812 122.445312h-35.902343v-17.492187h32.265625v-10.828125h-32.265625v-14.25h34.675781v-10.871094h-47.652344v64.269532h48.878906zm0 0"/><path d="m247.203125 133.273438 12.757813-48.046876 12.800781 48.046876h13.765625l15.605468-64.269532h-13.0625l-9.863281 44.890625-11.269531-44.890625h-15.429688l-11.75 44.144532-9.6875-44.144532h-13.285156l15.34375 64.269532zm0 0"/><path d="m332.117188 123.453125c-3.945313 0-7.078126-.996094-9.402344-2.980469-2.324219-1.988281-3.863282-5.101562-4.625-9.339844l-12.625 1.230469c.847656 7.1875 3.449218 12.660157 7.804687 16.414063 4.351563 3.757812 10.59375 5.632812 18.71875 5.632812 5.582031 0 10.242188-.78125 13.984375-2.34375 3.738282-1.5625 6.632813-3.953125 8.679688-7.167968 2.046875-3.214844 3.066406-6.664063 3.066406-10.34375 0-4.0625-.851562-7.476563-2.5625-10.238282-1.710938-2.761718-4.078125-4.9375-7.101562-6.53125-3.027344-1.59375-7.695313-3.136718-14.007813-4.625-6.3125-1.492187-10.285156-2.921875-11.921875-4.296875-1.289062-1.082031-1.929688-2.382812-1.929688-3.902343 0-1.664063.6875-2.996094 2.058594-3.988282 2.132813-1.546875 5.085938-2.324218 8.855469-2.324218 3.652344 0 6.394531.722656 8.21875 2.171874 1.828125 1.445313 3.019531 3.820313 3.574219 7.121094l12.976562-.570312c-.203125-5.902344-2.34375-10.621094-6.421875-14.160156-4.078125-3.535157-10.148437-5.300782-18.214843-5.300782-4.941407 0-9.15625.742188-12.648438 2.234375-3.492188 1.488281-6.167969 3.660157-8.023438 6.507813-1.855468 2.851562-2.78125 5.914062-2.78125 9.1875 0 5.085937 1.972657 9.394531 5.917969 12.929687 2.804688 2.515625 7.6875 4.632813 14.640625 6.359375 5.40625 1.34375 8.871094 2.277344 10.390625 2.804688 2.222657.789062 3.777344 1.714844 4.667969 2.78125.890625 1.070312 1.339844 2.363281 1.339844 3.882812 0 2.367188-1.0625 4.433594-3.179688 6.203125-2.121094 1.765625-5.269531 2.652344-9.449218 2.652344zm0 0"/></svg> Last 100 headlines here...</button></a>
          </div>



<hr>

    

                
          
          <div class="shadow-lg p-3 mb-5 bg-gray rounded">

<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8373809220012309"
     crossorigin="anonymous"></script>
<!-- infill 2 -->
<ins class="adsbygoogle"
     style="display:block"
     data-ad-client="ca-pub-8373809220012309"
     data-ad-slot="5535072674"
     data-ad-format="auto"
     data-full-width-responsive="true"></ins>
<script>
     (adsbygoogle = window.adsbygoogle || []).push({});
</script>
 
  

          </div>
          
           
 
		  
          
          



<hr>
 
 
 
          <!-- advert -->

        
          
          
          </section>

 <br> 
 
        <div class="shadow-lg p-3 mb-5 bg-gray rounded">

 
          </div>
          

          



      <section class="sidebar-instaram mt-7">

            <h5 class="title title-small flex-center-side">
              Recent articles...             </h5>
              
           
           
           
	                  <ul class="headlines-content">

	   <?	 
					        //Cat News
					      
					      	$i=0;

					       $news = array(
					          'posts_per_page'      => 10,
					          'orderby'          => 'desc',
					          
					          'cat' 			      => '-3283, -3377',

					          'offset'      => 12,
					        );  
					        
					        $news_posts = new WP_Query( $news );
					        
					        // The 2nd Loop
					
					        if ($news_posts->have_posts()) {
					           
					           while ($news_posts->have_posts()) : $news_posts->the_post(); 
					           
							   ++$i;

					           
  ?>
					           
					           
				<li>- <a href="<?php the_permalink(); ?>""><?php the_title( sprintf( '<p>', esc_url( get_permalink() ) ), '</p>' ); ?> </a></li>
                
               
 
				  
  				<?  
							   endwhile; 
					        }
					        ?>

            

         
            </ul>
          </section>
    
           
 



 </aside>
